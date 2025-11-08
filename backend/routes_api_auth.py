"""
WOVCC Flask Application - Auth API Routes
Handles all endpoints related to user authentication and management.
"""

from flask import Blueprint, jsonify, request
import logging
import datetime
from datetime import timezone
import os

from database import get_db, User, PendingRegistration
from auth import (
    hash_password, verify_password, generate_token, require_auth, 
    get_refresh_token_from_request, verify_token
)
from stripe_config import create_checkout_session, STRIPE_SECRET_KEY
from mailchimp import subscribe_to_newsletter

logger = logging.getLogger(__name__)
auth_api_bp = Blueprint('auth_api', __name__, url_prefix='/api')

# ----- Authentication API -----

@auth_api_bp.route('/auth/pre-register', methods=['POST'])
def pre_register():
    """Create a pending registration and return a Stripe Checkout session"""
    logger.info("[PRE-REGISTER] Starting pre-registration process")
    try:
        data = request.get_json()
        logger.info(f"[PRE-REGISTER] Received data: name={data.get('name')}, email={data.get('email')}, newsletter={data.get('newsletter')}")
        
        if not data or not data.get('email') or not data.get('password') or not data.get('name'):
            logger.error("[PRE-REGISTER] Missing required fields")
            return jsonify({'success': False, 'error': 'Name, email, and password are required'}), 400

        db = next(get_db())
        try:
            # Ensure email is not already registered
            existing_user = db.query(User).filter(User.email == data['email']).first()
            if existing_user:
                logger.warning(f"[PRE-REGISTER] Email already exists: {data['email']}")
                return jsonify({'success': False, 'error': 'An account with this email already exists'}), 400

            logger.info("[PRE-REGISTER] Creating pending registration...")
            # Create pending registration
            pending = PendingRegistration(
                name=data['name'],
                email=data['email'],
                password_hash=hash_password(data['password']),
                newsletter=data.get('newsletter', False)
            )
            db.add(pending)
            db.commit()
            db.refresh(pending)
            logger.info(f"[PRE-REGISTER] Pending registration created with ID: {pending.id}")

            # Create checkout session
            logger.info("[PRE-REGISTER] Creating Stripe checkout session...")
            session = create_checkout_session(
                customer_id=None,
                email=data['email'],
                user_id=None
            )
            logger.info(f"[PRE-REGISTER] Stripe session created: {session.id}")

            # Attach pending_id to session metadata
            try:
                import stripe
                stripe.api_key = STRIPE_SECRET_KEY
                logger.info(f"[PRE-REGISTER] Updating session metadata with pending_id={pending.id}")
                stripe.checkout.Session.modify(session.id, metadata={'pending_id': str(pending.id)})
                logger.info("[PRE-REGISTER] Session metadata updated successfully")
            except Exception as e:
                # If modifying fails, still return session; webhook can match by customer_email
                logger.error(f"[PRE-REGISTER] Failed to update session metadata: {e}")

            logger.info(f"[PRE-REGISTER] SUCCESS - Returning checkout URL: {session.url}")
            return jsonify({'success': True, 'checkout_url': session.url, 'session_id': session.id, 'pending_id': pending.id})
        finally:
            db.close()

    except Exception as e:
        logger.error(f"[PRE-REGISTER] ERROR: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_api_bp.route('/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        db = next(get_db())
        try:
            user = db.query(User).filter(User.email == data['email']).first()
            
            if not user:
                # Perform a dummy password hash to mitigate timing attacks
                verify_password('dummy_password_for_timing_attack_prevention', '$2b$12$DbmIZ/a5L5D2p0S21G9j5.UPX.z4wG1E.G8LCE123456789012345O')
                logger.warning(f"[LOGIN] User not found: {data['email']}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid email or password'
                }), 401
            
            if not verify_password(data['password'], user.password_hash):
                return jsonify({
                    'success': False,
                    'error': 'Invalid email or password'
                }), 401
            
            # Generate tokens
            tokens = generate_token(user.id, user.email, user.is_admin, include_refresh=True)
            
            # Separate refresh token for cookie
            refresh_token = tokens.pop('refresh_token')
            
            # Create response
            response = jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict(),
                **tokens
            })
            
            # Set refresh token as httpOnly, secure cookie
            response.set_cookie(
                'refresh_token',
                refresh_token,
                httponly=True,
                secure=not (os.environ.get('DEBUG', 'False').lower() == 'true'),  # Only use secure in production (HTTPS)
                samesite='Lax',  # Lax allows cookie on top-level navigation
                path='/',
                max_age=30 * 24 * 60 * 60  # 30 days in seconds
            )
            
            return response
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_api_bp.route('/auth/logout', methods=['POST'])
@require_auth
def logout(user):
    """Logout user (token invalidation handled client-side)"""
    response = jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })
    
    # Clear refresh token cookie
    response.set_cookie(
        'refresh_token',
        '',
        httponly=True,
        secure=not (os.environ.get('DEBUG', 'False').lower() == 'true'),
        samesite='Lax',
        path='/',
        max_age=0  # Expire immediately
    )
    
    return response


@auth_api_bp.route('/auth/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using httpOnly cookie refresh token"""
    try:
        # Get refresh token from httpOnly cookie
        refresh_token = get_refresh_token_from_request()
        
        if not refresh_token:
            return jsonify({
                'success': False,
                'error': 'No refresh token provided'
            }), 401
        
        # Verify refresh token
        payload = verify_token(refresh_token)
        
        if 'error' in payload:
            return jsonify({
                'success': False,
                'error': payload['error']
            }), 401
        
        # Verify token type
        if payload.get('type') != 'refresh':
            return jsonify({
                'success': False,
                'error': 'Invalid token type'
            }), 401
        
        # Get user from database
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == payload['user_id']).first()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 401
            
            # Generate new access token (no refresh token needed)
            tokens = generate_token(user.id, user.email, user.is_admin, include_refresh=False)
            
            return jsonify({
                'success': True,
                'message': 'Token refreshed',
                **tokens
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to refresh token'
        }), 500


@auth_api_bp.route('/user/profile', methods=['GET'])
@require_auth
def get_profile(user):
    """Get current user profile"""
    resp = jsonify({
        'success': True,
        'user': user.to_dict()
    })
    # No caching for user profile to prevent stale data
    resp.headers['Vary'] = 'Authorization'
    return resp


@auth_api_bp.route('/user/update', methods=['POST'])
@require_auth
def update_profile(user):
    """Update user profile"""
    try:
        data = request.get_json()
        
        db = next(get_db())
        try:
            if 'name' in data:
                user.name = data['name']
            if 'newsletter' in data:
                user.newsletter = data['newsletter']
            
            user.updated_at = datetime.datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully',
                'user': user.to_dict()
            })
        finally:
            db.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500