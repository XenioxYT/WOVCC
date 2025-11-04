"""
WOVCC API Server
Flask API for serving cricket data to the frontend
"""

# IMPORTANT: Load environment variables FIRST before other imports
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS
from scraper import scraper
from database import init_db, get_db, User
from auth import hash_password, verify_password, generate_token, require_auth, require_admin, get_current_user
from stripe_config import create_checkout_session, create_or_get_customer, verify_webhook_signature, STRIPE_SECRET_KEY
from database import PendingRegistration
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

# Initialize database on startup
init_db()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'WOVCC API',
        'version': '1.0.0'
    })


@app.route('/api/teams', methods=['GET'])
def get_teams():
    """Get list of all teams"""
    try:
        teams = scraper.get_teams()
        return jsonify({
            'success': True,
            'teams': teams,
            'count': len(teams)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/fixtures', methods=['GET'])
def get_fixtures():
    """Get upcoming fixtures
    
    Query params:
        team: team_id (optional, default: all)
    """
    team_id = request.args.get('team', None)
    
    if team_id and team_id.lower() == 'all':
        team_id = None
    
    try:
        fixtures = scraper.get_team_fixtures(team_id)
        return jsonify({
            'success': True,
            'fixtures': fixtures,
            'count': len(fixtures)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/results', methods=['GET'])
def get_results():
    """Get recent results
    
    Query params:
        team: team_id (optional, default: all)
        limit: number of results (optional, default: 10)
    """
    team_id = request.args.get('team', None)
    limit = request.args.get('limit', 10, type=int)
    
    if team_id and team_id.lower() == 'all':
        team_id = None
    
    try:
        results = scraper.get_team_results(team_id, limit)
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/data', methods=['GET'])
def get_all_data():
    """Get combined dataset (teams, fixtures, results) in one call.

    Query params:
        team: team_id (optional, default: all)
        limit: number of results (optional, default: 9999)
        source: 'live' (default) or 'file' to read existing scraped_data.json
    """
    team_id = request.args.get('team', None)
    limit = request.args.get('limit', 9999, type=int)
    source = request.args.get('source', 'live').lower()

    if team_id and team_id.lower() == 'all':
        team_id = None

    try:
        if source == 'file':
            # Serve directly from saved JSON if available
            file_path = os.path.join(os.path.dirname(__file__), 'scraped_data.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Optionally filter fixtures/results by team and apply limit
                fixtures = data.get('fixtures', [])
                results = data.get('results', [])
                if team_id:
                    fixtures = [fx for fx in fixtures if fx.get('team_id') == str(team_id)]
                    results = [rs for rs in results if rs.get('team_id') == str(team_id)]
                if isinstance(limit, int) and limit > 0:
                    results = results[:limit]

                return jsonify({
                    'success': True,
                    'last_updated': data.get('last_updated'),
                    'teams': data.get('teams', []),
                    'fixtures': fixtures,
                    'results': results
                })
            # If file not present, fall through to live scrape

        # Live scrape (default)
        teams = scraper.get_teams()
        fixtures = scraper.get_team_fixtures(team_id)
        results = scraper.get_team_results(team_id, limit)

        return jsonify({
            'success': True,
            'last_updated': datetime.now().isoformat(),
            'teams': teams,
            'fixtures': fixtures,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/match-status', methods=['GET'])
def match_status():
    """Check if there are matches scheduled for today"""
    try:
        has_matches = scraper.check_matches_today()
        return jsonify({
            'success': True,
            'has_matches_today': has_matches
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'has_matches_today': False
        }), 500


@app.route('/api/live-config', methods=['GET'])
def get_live_config():
    """Get current live match configuration"""
    try:
        config_file = os.path.join(os.path.dirname(__file__), 'live_config.json')
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            # Default config
            config = {
                'is_live': False,
                'livestream_url': '',
                'selected_match': None
            }
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/live-config', methods=['POST'])
@require_admin
def update_live_config(user):
    """Update live match configuration (admin only)
    
    Request body:
        {
            "is_live": boolean,
            "livestream_url": string (optional),
            "selected_match": object (optional)
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Load existing config or create new one
        config_file = os.path.join(os.path.dirname(__file__), 'live_config.json')
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {
                'is_live': False,
                'livestream_url': '',
                'selected_match': None
            }
        
        # Update config with provided data
        if 'is_live' in data:
            config['is_live'] = data['is_live']
        
        if 'livestream_url' in data:
            config['livestream_url'] = data['livestream_url']
        
        if 'selected_match' in data:
            config['selected_match'] = data['selected_match']
        
        # Add last updated timestamp
        config['last_updated'] = datetime.now().isoformat()
        
        # Save config
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Live configuration updated successfully',
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/clear-cache', methods=['POST'])
@require_admin
def clear_cache(user):
    """Clear all cached data (admin endpoint)"""
    try:
        import shutil
        cache_dir = 'cache'
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== Authentication Endpoints =====

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user
    
    Request body:
        {
            "name": string,
            "email": string,
            "password": string,
            "newsletter": boolean (optional)
        }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'Name, email, and password are required'
            }), 400
        
        db = next(get_db())
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == data['email']).first()
            if existing_user:
                return jsonify({
                    'success': False,
                    'error': 'An account with this email already exists'
                }), 400
            
            # Create new user
            # Create new user (legacy/manual registration)
            new_user = User(
                name=data['name'],
                email=data['email'],
                password_hash=hash_password(data['password']),
                newsletter=data.get('newsletter', False),
                membership_tier='Annual Member',
                is_member=False,  # Will be activated after payment
                is_admin=False
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            # Generate tokens
            tokens = generate_token(new_user.id, new_user.email, new_user.is_admin)

            return jsonify({
                'success': True,
                'message': 'Account created successfully',
                'user': new_user.to_dict(),
                **tokens
            }), 201
            
        finally:
            db.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/auth/pre-register', methods=['POST'])
def pre_register():
    """Create a pending registration and return a Stripe Checkout session for payment.

    This stores the registration data in a temporary table and creates a Checkout session
    with metadata containing the pending registration id. The actual user account will be
    created only after the webhook confirms payment.
    """
    try:
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password') or not data.get('name'):
            return jsonify({'success': False, 'error': 'Name, email, and password are required'}), 400

        db = next(get_db())
        try:
            # Ensure email is not already registered
            existing_user = db.query(User).filter(User.email == data['email']).first()
            if existing_user:
                return jsonify({'success': False, 'error': 'An account with this email already exists'}), 400

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

            # Create checkout session with pending_id in metadata
            session = create_checkout_session(
                customer_id=None,
                email=data['email'],
                user_id=None
            )

            # Inject pending_id into session metadata by creating session with metadata
            # Note: stripe.checkout.Session.create already supports metadata in create_checkout_session; to keep things simple
            # recreate session with metadata.pending_id if create_checkout_session didn't set it.
            # Safer approach: call stripe.checkout.Session.modify to attach metadata.
            try:
                import stripe
                stripe.api_key = STRIPE_SECRET_KEY
                stripe.checkout.Session.modify(session.id, metadata={'pending_id': str(pending.id)})
            except Exception:
                # If modifying fails, still return session; webhook can match by customer_email
                pass

            return jsonify({'success': True, 'checkout_url': session.url, 'session_id': session.id, 'pending_id': pending.id})
        finally:
            db.close()

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
            


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user
    
    Request body:
        {
            "email": string,
            "password": string
        }
    """
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
            
            if not user or not verify_password(data['password'], user.password_hash):
                return jsonify({
                    'success': False,
                    'error': 'Invalid email or password'
                }), 401
            
            # Generate tokens
            tokens = generate_token(user.id, user.email, user.is_admin)
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict(),
                **tokens
            })
            
        finally:
            db.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout(user):
    """Logout user (token invalidation handled client-side)"""
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })


@app.route('/api/auth/check-and-activate', methods=['POST'])
def check_and_activate():
    """
    Check if pending registration exists and activate it
    This is a fallback for when webhooks don't work in development
    """
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email required'}), 400
        
        db = next(get_db())
        try:
            # Check if user already exists
            user = db.query(User).filter(User.email == email).first()
            if user:
                return jsonify({
                    'success': True,
                    'activated': True,
                    'message': 'Account already active'
                })
            
            # Check for pending registration
            pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()
            if not pending:
                return jsonify({
                    'success': False,
                    'activated': False,
                    'message': 'No registration found'
                })
            
            # Activate the pending registration
            from dateutil.relativedelta import relativedelta
            now = datetime.utcnow()
            expiry = now + relativedelta(years=1)
            
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
            db.delete(pending)
            db.commit()
            
            return jsonify({
                'success': True,
                'activated': True,
                'message': 'Account activated successfully'
            })
            
        finally:
            db.close()
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/profile', methods=['GET'])
@require_auth
def get_profile(user):
    """Get current user profile"""
    return jsonify({
        'success': True,
        'user': user.to_dict()
    })


@app.route('/api/user/update', methods=['POST'])
@require_auth
def update_profile(user):
    """Update user profile
    
    Request body:
        {
            "name": string (optional),
            "newsletter": boolean (optional)
        }
    """
    try:
        data = request.get_json()
        
        db = next(get_db())
        try:
            if 'name' in data:
                user.name = data['name']
            if 'newsletter' in data:
                user.newsletter = data['newsletter']
            
            user.updated_at = datetime.utcnow()
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


# ===== Stripe Payment Endpoints =====

@app.route('/api/payments/create-checkout', methods=['POST'])
@require_auth
def create_payment_checkout(user):
    """Create Stripe Checkout session for membership payment"""
    try:
        if not STRIPE_SECRET_KEY:
            return jsonify({
                'success': False,
                'error': 'Stripe is not configured'
            }), 500
        
        db = next(get_db())
        try:
            # Get or create Stripe customer
            if user.stripe_customer_id:
                customer_id = user.stripe_customer_id
            else:
                stripe_customer = create_or_get_customer(user.email, user.name)
                user.stripe_customer_id = stripe_customer.id
                db.commit()
                customer_id = stripe_customer.id
            
            # Create checkout session
            session = create_checkout_session(
                customer_id=customer_id,
                user_id=user.id
            )
            
            return jsonify({
                'success': True,
                'checkout_url': session.url,
                'session_id': session.id
            })
        finally:
            db.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/payments/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    logger.info("[WEBHOOK] Received event from Stripe")
    
    # Verify webhook signature
    event = verify_webhook_signature(payload, sig_header)
    if not event:
        # If verification fails but webhook secret is set, reject the request
        from stripe_config import STRIPE_WEBHOOK_SECRET
        if STRIPE_WEBHOOK_SECRET:
            logger.error("[WEBHOOK] Signature verification failed!")
            return jsonify({
                'success': False,
                'error': 'Invalid webhook signature'
            }), 400
        else:
            # If no webhook secret is set, parse the payload directly (development only!)
            logger.warning("[WEBHOOK] Webhook signature verification is disabled!")
            try:
                import json as json_module
                event = json_module.loads(payload)
            except Exception as e:
                logger.error(f"[WEBHOOK] Failed to parse payload: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid payload'
                }), 400
    
    event_type = event.get('type', 'unknown')
    logger.info(f"[WEBHOOK] Event type: {event_type}")
    
    try:
        # Handle checkout session completed
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            session_id = session.get('id')
            payment_status = session.get('payment_status')
            user_id_str = session.get('metadata', {}).get('user_id')
            
            logger.info(f"[WEBHOOK] Session ID: {session_id}")
            logger.info(f"[WEBHOOK] Payment status: {payment_status}")
            logger.info(f"[WEBHOOK] User ID from metadata: {user_id_str}")
            
            pending_id_str = session.get('metadata', {}).get('pending_id')

            # Case 1: existing user (renewal) referenced by user_id
            if payment_status == 'paid' and user_id_str:
                try:
                    user_id = int(user_id_str)
                except (ValueError, TypeError):
                    logger.error(f"[WEBHOOK] Invalid user_id in metadata: {user_id_str}")
                    return jsonify({'success': False, 'error': 'Invalid user_id'}), 400
                
                db = next(get_db())
                try:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        from dateutil.relativedelta import relativedelta
                        now = datetime.utcnow()
                        user.is_member = True
                        user.payment_status = 'active'
                        user.membership_start_date = now
                        user.membership_expiry_date = now + relativedelta(years=1)
                        user.updated_at = now
                        db.commit()
                        logger.info(f"[WEBHOOK] User {user_id} ({user.email}) membership activated until {user.membership_expiry_date}!")
                    else:
                        logger.error(f"[WEBHOOK] User {user_id} not found in database")
                finally:
                    db.close()
            else:
                # Case 2: pending registration flow - create user after successful payment
                if payment_status == 'paid' and pending_id_str:
                    try:
                        pending_id = int(pending_id_str)
                    except (ValueError, TypeError):
                        logger.error(f"[WEBHOOK] Invalid pending_id in metadata: {pending_id_str}")
                        return jsonify({'success': False, 'error': 'Invalid pending_id'}), 400

                    db = next(get_db())
                    try:
                        pending = db.query(PendingRegistration).filter(PendingRegistration.id == pending_id).first()
                        if pending:
                            from dateutil.relativedelta import relativedelta
                            now = datetime.utcnow()
                            expiry = now + relativedelta(years=1)
                            
                            # If a user with that email already exists, just activate membership
                            existing_user = db.query(User).filter(User.email == pending.email).first()
                            if existing_user:
                                existing_user.is_member = True
                                existing_user.payment_status = 'active'
                                existing_user.membership_start_date = now
                                existing_user.membership_expiry_date = expiry
                                existing_user.updated_at = now
                                logger.info(f"[WEBHOOK] Existing user {existing_user.id} ({existing_user.email}) activated from pending until {expiry}")
                            else:
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
                                logger.info(f"[WEBHOOK] Created new user from pending registration: {pending.email}, membership until {expiry}")

                            # Remove pending registration
                            try:
                                db.delete(pending)
                            except Exception:
                                pass

                            db.commit()
                        else:
                            logger.error(f"[WEBHOOK] Pending registration {pending_id} not found")
                    finally:
                        db.close()
                else:
                    logger.warning("[WEBHOOK] Payment not completed or no user_id/pending_id in metadata")
        
        # Handle payment intent succeeded (alternative)
        elif event_type == 'payment_intent.succeeded':
            logger.info("[WEBHOOK] Payment intent succeeded (no action needed for Checkout mode)")
        
        # Handle checkout session expired
        elif event_type == 'checkout.session.expired':
            session_id = event['data']['object'].get('id')
            logger.warning(f"[WEBHOOK] Checkout session expired: {session_id}")
        
        # Handle other events
        else:
            logger.info(f"[WEBHOOK] Unhandled event type: {event_type}")
        
        return jsonify({'success': True, 'received': True})
        
    except Exception as e:
        logger.error(f"[WEBHOOK] Error processing webhook: {type(e).__name__}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    logger.info(f"Starting WOVCC API on port {PORT}...")
    logger.info(f"Debug mode: {DEBUG}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)

