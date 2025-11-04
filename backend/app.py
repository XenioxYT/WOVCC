"""
WOVCC Web Application
Flask app for serving server-side rendered pages with Jinja2 templates
This complements api.py which handles API endpoints
"""

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import os

# Import existing modules for integration
from auth import require_auth, get_current_user
from database import init_db

app = Flask(__name__)

# Configure static files to serve from parent directory
# We'll manually handle static routes for styles, scripts, and assets
CORS(app)

# Initialize database on startup
init_db()

# Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5001))  # Use different port from api.py


# Routes for static assets (styles, scripts, images)
@app.route('/styles/<path:filename>')
def serve_styles(filename):
    """Serve CSS files from styles directory"""
    styles_dir = os.path.join(os.path.dirname(__file__), '..', 'styles')
    return send_from_directory(styles_dir, filename)


@app.route('/scripts/<path:filename>')
def serve_scripts(filename):
    """Serve JavaScript files from scripts directory"""
    scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    return send_from_directory(scripts_dir, filename)


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve asset files (images, etc) from assets directory"""
    assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
    return send_from_directory(assets_dir, filename)


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
    """Join/Renew membership page"""
    return render_template('join.html')


@app.route('/admin')
def admin():
    """Admin page - requires authentication"""
    return render_template('admin.html')


# Health check
@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'service': 'WOVCC Web App'}


if __name__ == '__main__':
    print(f"🏏 WOVCC Web Application starting on http://localhost:{PORT}")
    print(f"   Debug mode: {DEBUG}")
    print(f"   Templates: {app.template_folder}")
    print(f"   Static (styles): {app.static_folder}")
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
