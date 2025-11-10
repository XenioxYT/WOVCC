"""
WOVCC Flask Application - Webhooks API Routes
Handles all incoming webhooks, e.g., from Stripe.
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime, timezone

from database import get_db, User, PendingRegistration
from stripe_config import verify_webhook_signature, STRIPE_WEBHOOK_SECRET
from mailchimp import subscribe_to_newsletter
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)
webhooks_api_bp = Blueprint('webhooks_api', __name__, url_prefix='/api/payments')

# ----- Stripe Payment API -----

@webhooks_api_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    # Verify webhook signature - ALWAYS required for production security
    if not STRIPE_WEBHOOK_SECRET:
        logger.critical("[WEBHOOK] STRIPE_WEBHOOK_SECRET is not configured - webhooks disabled for security")
        return jsonify({
            'success': False,
            'error': 'Webhook endpoint not configured'
        }), 503
    
    event = verify_webhook_signature(payload, sig_header)
    if not event:
        logger.error("[WEBHOOK] Invalid webhook signature")
        return jsonify({
            'success': False,
            'error': 'Invalid webhook signature'
        }), 400
    
    event_type = event.get('type', 'unknown')
    
    try:
        # Handle checkout session completed
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            session_id = session.get('id')
            payment_status = session.get('payment_status')
            pending_id_str = session.get('metadata', {}).get('pending_id')
            user_id_str = session.get('metadata', {}).get('user_id')
            spouse_card_only = session.get('metadata', {}).get('spouse_card_only') == 'true'
            
            logger.info(f"[WEBHOOK] Checkout session {session_id}: payment_status={payment_status}, pending_id={pending_id_str}, user_id={user_id_str}, spouse_card_only={spouse_card_only}")

            # Handle additional card only purchase (for existing members)
            if payment_status == 'paid' and spouse_card_only and user_id_str:
                try:
                    user_id = int(user_id_str)
                except (ValueError, TypeError):
                    logger.error(f"[WEBHOOK] Invalid user_id in spouse card purchase: {user_id_str}")
                    return jsonify({'success': False, 'error': 'Invalid user_id'}), 400
                
                db = next(get_db())
                try:
                    user = db.query(User).filter(User.id == user_id).first()
                    if not user:
                        logger.error(f"[WEBHOOK] User not found for ID: {user_id}")
                        return jsonify({'success': False, 'error': 'User not found'}), 404
                    
                    logger.info(f"[WEBHOOK] Setting additional card flag for user {user.email}")
                    user.has_spouse_card = True
                    user.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    logger.info(f"[WEBHOOK] Successfully added additional card for {user.email}")
                finally:
                    db.close()
            
            # Create user account after successful payment
            elif payment_status == 'paid' and pending_id_str:
                try:
                    pending_id = int(pending_id_str)
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Invalid pending_id'}), 400

                db = next(get_db())
                try:
                    pending = db.query(PendingRegistration).filter(PendingRegistration.id == pending_id).first()
                    if not pending:
                        logger.error(f"[WEBHOOK] Pending registration not found for ID: {pending_id}")
                        return jsonify({'success': False, 'error': 'Pending registration not found'}), 404
                    
                    logger.info(f"[WEBHOOK] Found pending registration for {pending.email}")
                    
                    now = datetime.now(timezone.utc)
                    expiry = now + relativedelta(years=1)
                    
                    # Check if user already exists (edge case)
                    existing_user = db.query(User).filter(User.email == pending.email).first()
                    if existing_user:
                        logger.warning(f"[WEBHOOK] User {pending.email} already exists, updating membership")
                        # Update existing user's membership
                        existing_user.is_member = True
                        existing_user.payment_status = 'active'
                        existing_user.membership_start_date = now
                        existing_user.membership_expiry_date = expiry
                        existing_user.updated_at = now
                        
                        # Subscribe to newsletter if requested and not already subscribed
                        if pending.newsletter:
                            try:
                                subscribe_to_newsletter(existing_user.email, existing_user.name)
                                logger.info(f"Subscribed {existing_user.email} to newsletter after payment")
                            except Exception as e:
                                logger.error(f"Failed to subscribe {existing_user.email} to newsletter: {e}")
                    else:
                        # Create new user account with activation token for secure first login
                        logger.info(f"[WEBHOOK] Creating new user account for {pending.email}")
                        new_user = User(
                            name=pending.name,
                            email=pending.email,
                            password_hash=pending.password_hash,
                            activation_token=pending.activation_token,  # Transfer token for secure activation
                            newsletter=pending.newsletter,
                            membership_tier='Annual Member',
                            is_member=True,
                            is_admin=False,
                            payment_status='active',
                            has_spouse_card=pending.include_spouse_card,
                            membership_start_date=now,
                            membership_expiry_date=expiry
                        )
                        db.add(new_user)
                        db.flush()  # Flush to get the user ID before committing
                        logger.info(f"[WEBHOOK] User created with ID: {new_user.id}")
                        
                        # Subscribe to newsletter if requested
                        if pending.newsletter:
                            try:
                                subscribe_to_newsletter(new_user.email, new_user.name)
                                logger.info(f"[WEBHOOK] Subscribed {new_user.email} to newsletter")
                            except Exception as e:
                                logger.error(f"[WEBHOOK] Failed to subscribe {new_user.email} to newsletter: {e}")

                    # Remove pending registration
                    db.delete(pending)
                    db.commit()
                    logger.info(f"[WEBHOOK] Successfully activated account for {pending.email}")
                finally:
                    db.close()
        
        # Handle payment intent succeeded (alternative)
        elif event_type == 'payment_intent.succeeded':
            pass  # No action needed for Checkout mode
        
        # Handle checkout session expired
        elif event_type == 'checkout.session.expired':
            session = event['data']['object']
            session_id = session.get('id')
            pending_id_str = session.get('metadata', {}).get('pending_id')
            
            # Clean up expired pending registration
            if pending_id_str:
                try:
                    pending_id = int(pending_id_str)
                    db = next(get_db())
                    try:
                        pending = db.query(PendingRegistration).filter(PendingRegistration.id == pending_id).first()
                        if pending:
                            db.delete(pending)
                            db.commit()
                    finally:
                        db.close()
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid pending_id in expired session metadata: {pending_id_str}, error: {e}")
        
        return jsonify({'success': True, 'received': True})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {type(e).__name__}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500