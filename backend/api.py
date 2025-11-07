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

            # Check for existing pending registration and reuse/update it
            pending = db.query(PendingRegistration).filter(PendingRegistration.email == data['email']).with_for_update().first()
            if pending:
                # Update existing pending registration with new data
                pending.name = data['name']
                pending.password_hash = hash_password(data['password'])
                pending.newsletter = data.get('newsletter', False)
                pending.created_at = datetime.now(timezone.utc)  # Update timestamp
            else:
                # Create new pending registration
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


# ===== Admin User Management Endpoints =====

@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def get_admin_stats(user):
    """Get member statistics for admin dashboard"""
    try:
        db = next(get_db())
        try:
            from sqlalchemy import func, or_
            from datetime import datetime, timedelta
            
            # Total members
            total_members = db.query(User).filter(User.is_member == True).count()
            
            # Active members (not expired)
            now = datetime.utcnow()
            active_members = db.query(User).filter(
                User.is_member == True,
                User.payment_status == 'active',
                or_(User.membership_expiry_date.is_(None), User.membership_expiry_date > now)
            ).count()
            
            # Expired members
            expired_members = db.query(User).filter(
                User.is_member == True,
                User.membership_expiry_date < now
            ).count()
            
            # New members this month
            first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            new_members_this_month = db.query(User).filter(
                User.join_date >= first_of_month
            ).count()
            
            # Payment status breakdown
            payment_status_counts = db.query(
                User.payment_status,
                func.count(User.id)
            ).group_by(User.payment_status).all()
            
            payment_status_breakdown = {status: count for status, count in payment_status_counts}
            
            # Newsletter subscribers
            newsletter_subscribers = db.query(User).filter(User.newsletter == True).count()
            
            # Recent signups (last 10)
            recent_signups = db.query(User).order_by(User.created_at.desc()).limit(10).all()
            
            # Members expiring soon (within 30 days)
            thirty_days_from_now = now + timedelta(days=30)
            expiring_soon = db.query(User).filter(
                User.is_member == True,
                User.membership_expiry_date.isnot(None),
                User.membership_expiry_date > now,
                User.membership_expiry_date <= thirty_days_from_now
            ).count()
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_members': total_members,
                    'active_members': active_members,
                    'expired_members': expired_members,
                    'new_members_this_month': new_members_this_month,
                    'newsletter_subscribers': newsletter_subscribers,
                    'expiring_soon': expiring_soon,
                    'payment_status_breakdown': payment_status_breakdown,
                    'recent_signups': [u.to_dict() for u in recent_signups]
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/users', methods=['GET'])
@require_admin
def get_all_users(user):
    """Get all users with filtering and pagination"""
    try:
        from sqlalchemy import or_
        search = request.args.get('search', '').strip()
        filter_type = request.args.get('filter', 'all')
        sort = request.args.get('sort', 'join_date')
        order = request.args.get('order', 'desc')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        db = next(get_db())
        try:
            query = db.query(User)
            
            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        User.name.ilike(search_term),
                        User.email.ilike(search_term)
                    )
                )
            
            # Apply type filter
            now = datetime.utcnow()
            if filter_type == 'members':
                query = query.filter(User.is_member == True)
            elif filter_type == 'non-members':
                query = query.filter(User.is_member == False)
            elif filter_type == 'active':
                query = query.filter(
                    User.is_member == True,
                    User.payment_status == 'active',
                    or_(User.membership_expiry_date.is_(None), User.membership_expiry_date > now)
                )
            elif filter_type == 'expired':
                query = query.filter(
                    User.is_member == True,
                    User.membership_expiry_date < now
                )
            elif filter_type == 'admins':
                query = query.filter(User.is_admin == True)
            
            # Apply sorting
            if sort == 'name':
                query = query.order_by(User.name.desc() if order == 'desc' else User.name.asc())
            elif sort == 'email':
                query = query.order_by(User.email.desc() if order == 'desc' else User.email.asc())
            elif sort == 'join_date':
                query = query.order_by(User.join_date.desc() if order == 'desc' else User.join_date.asc())
            elif sort == 'expiry_date':
                query = query.order_by(User.membership_expiry_date.desc() if order == 'desc' else User.membership_expiry_date.asc())
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            users = query.offset(offset).limit(per_page).all()
            
            return jsonify({
                'success': True,
                'users': [u.to_dict(include_sensitive=True) for u in users],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(admin_user, user_id):
    """Update user details (admin only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Update fields
            if 'name' in data:
                user.name = data['name']
            if 'email' in data:
                existing = db.query(User).filter(User.email == data['email'], User.id != user_id).first()
                if existing:
                    return jsonify({
                        'success': False,
                        'error': 'Email already in use'
                    }), 400
                user.email = data['email']
            if 'is_member' in data:
                user.is_member = data['is_member']
            if 'is_admin' in data:
                user.is_admin = data['is_admin']
            if 'newsletter' in data:
                user.newsletter = data['newsletter']
            if 'payment_status' in data:
                user.payment_status = data['payment_status']
            if 'membership_tier' in data:
                user.membership_tier = data['membership_tier']
            if 'membership_expiry_date' in data:
                if data['membership_expiry_date']:
                    from dateutil import parser
                    user.membership_expiry_date = parser.parse(data['membership_expiry_date'])
                else:
                    user.membership_expiry_date = None
            
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
            
            return jsonify({
                'success': True,
                'message': 'User updated successfully',
                'user': user.to_dict(include_sensitive=True)
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(admin_user, user_id):
    """Delete a user (admin only)"""
    try:
        if admin_user.id == user_id:
            return jsonify({
                'success': False,
                'error': 'Cannot delete your own account'
            }), 400
        
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            db.delete(user)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== Stripe Payment Endpoints =====

@app.route('/api/payments/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    # Verify webhook signature
    event = verify_webhook_signature(payload, sig_header)
    if not event:
        # If verification fails but webhook secret is set, reject the request
        from stripe_config import STRIPE_WEBHOOK_SECRET
        if STRIPE_WEBHOOK_SECRET:
            return jsonify({
                'success': False,
                'error': 'Invalid webhook signature'
            }), 400
        else:
            # If no webhook secret is set, parse the payload directly (development only!)
            try:
                import json as json_module
                event = json_module.loads(payload)
            except Exception as e:
                logger.error(f"Failed to parse webhook payload: {e}")
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

            # Create user account after successful payment
            if payment_status == 'paid' and pending_id_str:
                try:
                    pending_id = int(pending_id_str)
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Invalid pending_id'}), 400

                db = next(get_db())
                try:
                    pending = db.query(PendingRegistration).filter(PendingRegistration.id == pending_id).first()
                    if pending:
                        from dateutil.relativedelta import relativedelta
                        now = datetime.utcnow()
                        expiry = now + relativedelta(years=1)
                        
                        # Check if user already exists (edge case)
                        existing_user = db.query(User).filter(User.email == pending.email).first()
                        if existing_user:
                            # Update existing user's membership
                            existing_user.is_member = True
                            existing_user.payment_status = 'active'
                            existing_user.membership_start_date = now
                            existing_user.membership_expiry_date = expiry
                            existing_user.updated_at = now
                        else:
                            # Create new user account
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

                        # Remove pending registration
                        db.delete(pending)
                        db.commit()
                finally:
                    db.close()
        
        # Handle payment intent succeeded (alternative)
        elif event_type == 'payment_intent.succeeded':
            pass  # No action needed for Checkout mode
        
        # Handle checkout session expired
        elif event_type == 'checkout.session.expired':
            pass  # Could implement cleanup here
        
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

