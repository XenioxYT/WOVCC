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
    
    # Verify webhook signature
    event = verify_webhook_signature(payload, sig_header)
    if not event:
        # If verification fails but webhook secret is set, reject the request
        if STRIPE_WEBHOOK_SECRET:
            logger.error("[WEBHOOK] Invalid signature")
            return jsonify({
                'success': False,
                'error': 'Invalid webhook signature'
            }), 400
        else:
            # If no webhook secret is set, parse the payload directly (development only!)
            try:
                import json as json_module
                event = json_module.loads(payload)
                logger.warning("[WEBHOOK] No webhook secret set, parsing payload directly (DEV MODE)")
            except Exception as e:
                logger.error(f"[WEBHOOK] Failed to parse webhook payload: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid payload'
                }), 400
    
    event_type = event.get('type', 'unknown')
    
    try:
        # Handle checkout session completed
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            session_id = session.get('id')
            payment_status = session.get('payment_status')
            pending_id_str = session.get('metadata', {}).get('pending_id')
            
            logger.info(f"[WEBHOOK] Checkout session {session_id}: payment_status={payment_status}, pending_id={pending_id_str}")

            # Create user account after successful payment
            if payment_status == 'paid' and pending_id_str:
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
                        # Create new user account
                        logger.info(f"[WEBHOOK] Creating new user account for {pending.email}")
                        new_user = User(
                            name=pending.name,
                            email=pending.email,
                            password_hash=pending.password_hash,
                            newsletter=pending.newsletter,
                            membership_tier='Annual Member',
                            is_member=True,
                            is_admin=False,
                            payment_status='active',
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