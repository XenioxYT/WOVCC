"""
WOVCC API Server
Flask API for serving cricket data to the frontend
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from scraper import scraper
from database import init_db, get_db, User
from auth import hash_password, verify_password, generate_token, require_auth, require_admin, get_current_user
from stripe_config import create_checkout_session, create_or_get_customer, verify_webhook_signature, STRIPE_SECRET_KEY
import os
import json
from datetime import datetime

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
    try:
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')
        
        event = verify_webhook_signature(payload, sig_header)
        if not event:
            return jsonify({
                'success': False,
                'error': 'Invalid webhook signature'
            }), 400
        
        # Handle different event types
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = int(session['metadata'].get('user_id', 0))
            
            if user_id:
                db = next(get_db())
                try:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        user.is_member = True
                        user.payment_status = 'active'
                        user.updated_at = datetime.utcnow()
                        db.commit()
                finally:
                    db.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
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
    print(f"Starting WOVCC API on port {PORT}...")
    print(f"Debug mode: {DEBUG}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)

