"""
WOVCC Flask Application
Combined web server providing:
1. Server-side rendered pages with Jinja2 templates
2. JSON API endpoints for cricket data, authentication, and payments
"""

# IMPORTANT: Load environment variables FIRST before other imports
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, send_from_directory, jsonify, request
from flask_cors import CORS
import os
import json
import logging
from datetime import datetime

# Import application modules
from scraper import scraper
from database import init_db, get_db, User, PendingRegistration
from auth import hash_password, verify_password, generate_token, require_auth, require_admin, get_current_user
from stripe_config import create_checkout_session, create_or_get_customer, verify_webhook_signature, STRIPE_SECRET_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for API access

# Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

# Initialize database on startup
init_db()


# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add security and default cache-control headers to all responses"""
    # Add default no-cache headers for dynamic content
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    # Prevent MIME-type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # Enable XSS protection
# response.headers['X-XSS-Protection'] = '1; mode=block'
# Add a basic Content-Security-Policy for better XSS protection.
csp = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com;"
)
response.headers['Content-Security-Policy'] = csp
    # HSTS (only in production with HTTPS)
    if not DEBUG and request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Permissions policy
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response


# Routes for static assets (styles, scripts, images)
@app.route('/styles/<path:filename>')
def serve_styles(filename):
    """Serve CSS files from styles directory with caching"""
    styles_dir = os.path.join(os.path.dirname(__file__), '..', 'styles')
    response = send_from_directory(styles_dir, filename)
    # Cache for 1 year (aggressive caching for CSS)
    response.cache_control.max_age = 31536000
    response.cache_control.public = True
    return response


@app.route('/scripts/<path:filename>')
def serve_scripts(filename):
    """Serve JavaScript files from scripts directory with caching"""
    scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    response = send_from_directory(scripts_dir, filename)
    # Cache for 1 hour (safer caching for JS to allow updates)
    response.cache_control.max_age = 3600
    response.cache_control.public = True
    return response


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve asset files (images, etc) from assets directory with caching"""
    assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
    response = send_from_directory(assets_dir, filename)
    # Cache for 1 hour (safer caching for images without versioning)
    response.cache_control.max_age = 3600
    response.cache_control.public = True
    return response


# Page routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/members')
def members():
    """Members page - shows login form or member content based on auth"""
    return render_template('members.html')


@app.route('/matches')
def matches():
    """Matches page"""
    return render_template('matches.html')


@app.route('/join')
def join():
    """Join membership page"""
    return render_template('join.html')


@app.route('/join/activate')
def activate():
    """Account activation page after payment"""
    return render_template('activate.html')


@app.route('/admin')
def admin():
    """Admin page - requires authentication"""
    return render_template('admin.html')


# SEO and utility routes
@app.route('/robots.txt')
def robots():
    """Robots.txt file for search engines"""
    return """User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin

Sitemap: {}/sitemap.xml
""".format(request.url_root.rstrip('/')), 200, {'Content-Type': 'text/plain; charset=utf-8'}


# Health check
@app.route('/health')
@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'WOVCC Application',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat()
    })


# ========================================
# API ENDPOINTS
# ========================================

# ----- Cricket Data API -----

@app.route('/api/teams', methods=['GET'])
def get_teams():
    """Get list of all teams"""
    try:
        teams = scraper.get_teams()
        resp = jsonify({
            'success': True,
            'teams': teams,
            'count': len(teams)
        })
        # Cache for 10 minutes (teams rarely change)
        resp.cache_control.max_age = 600
        resp.cache_control.public = True
        return resp
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
        resp = jsonify({
            'success': True,
            'fixtures': fixtures,
            'count': len(fixtures)
        })
        # Cache for 5 minutes (fixtures can change)
        resp.cache_control.max_age = 300
        resp.cache_control.public = True
        return resp
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
        resp = jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        # Cache for 5 minutes (results update frequently)
        resp.cache_control.max_age = 300
        resp.cache_control.public = True
        return resp
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

                resp = jsonify({
                    'success': True,
                    'last_updated': data.get('last_updated'),
                    'teams': data.get('teams', []),
                    'fixtures': fixtures,
                    'results': results
                })
                # Cache file responses for 5 minutes
                resp.cache_control.max_age = 300
                resp.cache_control.public = True
                return resp
            # If file not present, fall through to live scrape

        # Live scrape (default)
        teams = scraper.get_teams()
        fixtures = scraper.get_team_fixtures(team_id)
        results = scraper.get_team_results(team_id, limit)

        resp = jsonify({
            'success': True,
            'last_updated': datetime.now().isoformat(),
            'teams': teams,
            'fixtures': fixtures,
            'results': results
        })
        # Cache for 5 minutes
        resp.cache_control.max_age = 300
        resp.cache_control.public = True
        return resp
        
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
        resp = jsonify({
            'success': True,
            'has_matches_today': has_matches
        })
        # Cache for 2 minutes (checked frequently but doesn't change often)
        resp.cache_control.max_age = 120
        resp.cache_control.public = True
        return resp
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
        
        resp = jsonify({
            'success': True,
            'config': config
        })
        # Cache for 1 minute (needs to be relatively fresh for live updates)
        resp.cache_control.max_age = 60
        resp.cache_control.public = True
        return resp
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


# ----- Authentication API -----

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user (legacy/manual registration)
    
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

            # Create checkout session
            session = create_checkout_session(
                customer_id=None,
                email=data['email'],
                user_id=None
            )

            # Attach pending_id to session metadata
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
    """Check if pending registration exists and activate it
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
    resp = jsonify({
        'success': True,
        'user': user.to_dict()
    })
    # Private cache only (no shared cache for user data)
    resp.cache_control.private = True
    resp.cache_control.max_age = 60
    resp.headers['Vary'] = 'Authorization'
    return resp


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


# ----- Stripe Payment API -----

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
            pending_id_str = session.get('metadata', {}).get('pending_id')
            
            logger.info(f"[WEBHOOK] Session ID: {session_id}")
            logger.info(f"[WEBHOOK] Payment status: {payment_status}")
            logger.info(f"[WEBHOOK] Pending ID from metadata: {pending_id_str}")

            # Create user account after successful payment
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
                        
                        # Check if user already exists (edge case)
                        existing_user = db.query(User).filter(User.email == pending.email).first()
                        if existing_user:
                            # Update existing user's membership
                            existing_user.is_member = True
                            existing_user.payment_status = 'active'
                            existing_user.membership_start_date = now
                            existing_user.membership_expiry_date = expiry
                            existing_user.updated_at = now
                            logger.info(f"[WEBHOOK] Existing user {existing_user.id} ({existing_user.email}) activated, membership until {expiry}")
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
                            logger.info(f"[WEBHOOK] Created new user: {pending.email}, membership until {expiry}")

                        # Remove pending registration
                        db.delete(pending)
                        db.commit()
                    else:
                        logger.error(f"[WEBHOOK] Pending registration {pending_id} not found")
                finally:
                    db.close()
            else:
                logger.warning("[WEBHOOK] Payment not completed or no pending_id in metadata")
        
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


# ----- Error Handlers -----

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors - return HTML for pages, JSON for API"""
    # Check if request is for API endpoint
    if request.path.startswith('/api/') or request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'success': False,
            'error': 'Endpoint not found'
        }), 404
    # Return HTML error page for regular page requests
    try:
        return render_template('404.html'), 404
    except Exception:
        return "<h1>404 - Page Not Found</h1><p>The page you're looking for doesn't exist.</p><a href='/'>Go Home</a>", 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors - return HTML for pages, JSON for API"""
    logger.error(f"Internal server error: {e}", exc_info=True)
    # Check if request is for API endpoint
    if request.path.startswith('/api/') or request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    # Return HTML error page for regular page requests
    try:
        return render_template('500.html', error=str(e) if DEBUG else None), 500
    except Exception:
        return "<h1>500 - Server Error</h1><p>Something went wrong on our end. Please try again later.</p><a href='/'>Go Home</a>", 500


# ----- Application Entry Point -----

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("🏏 WOVCC Flask Application Starting")
    logger.info("="*60)
    logger.info(f"Server URL: http://localhost:{PORT}")
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"Templates: {app.template_folder}")
    logger.info("")
    logger.info("Available Pages:")
    logger.info("  • Home:    http://localhost:{PORT}/")
    logger.info(f"  • Matches: http://localhost:{PORT}/matches")
    logger.info(f"  • Join:    http://localhost:{PORT}/join")
    logger.info(f"  • Members: http://localhost:{PORT}/members")
    logger.info(f"  • Admin:   http://localhost:{PORT}/admin")
    logger.info("")
    logger.info("API Endpoints: http://localhost:{PORT}/api/*")
    logger.info("="*60)
    
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
