"""
WOVCC Flask Application
Main application factory.
Initialises the Flask app, database, and registers all blueprints.
"""

# IMPORTANT: Load environment variables FIRST before other imports
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, send_from_directory, jsonify, request
from flask_cors import CORS
import os
import logging
from datetime import datetime

# Import application modules
from database import init_db
from signup_logger import init_signup_activity_table

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

# Enable CORS with credentials support for httpOnly cookies
CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'http://127.0.0.1:5000', 'https://wovcc.co.uk', 'https://www.wovcc.co.uk'])

# Initialize database on startup
init_db()
init_signup_activity_table()

# ========================================
# Import and Register Blueprints
# ========================================
from routes_pages import pages_bp
from routes_api_cricket import cricket_api_bp
from routes_api_auth import auth_api_bp
from routes_api_admin import admin_api_bp
from routes_api_events import events_api_bp
from routes_api_webhooks import webhooks_api_bp
from routes_api_contact import contact_bp

app.register_blueprint(pages_bp)
app.register_blueprint(cricket_api_bp)
app.register_blueprint(auth_api_bp)
app.register_blueprint(admin_api_bp)
app.register_blueprint(events_api_bp)
app.register_blueprint(webhooks_api_bp)
app.register_blueprint(contact_bp)


# ========================================
# Security headers middleware
# ========================================
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
    # Updated Content-Security-Policy:
    # - Remove 'unsafe-inline' for scripts
    # - Allow external marked.js CDN
    # - Permit inline styles via nonce-based attributes (templates/scripts should avoid new inline JS)
    # IMPORTANT:
    # - Allow API calls to your Cloudflare-tunnelled backend and external API hostname.
    # - Keep localhost targets for local/dev usage.
    # - Keep cdn.jsdelivr.net for external scripts.
    # - Update this if you introduce new domains.
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' http://localhost:5000 http://127.0.0.1:5000 https://wovcc.xeniox.uk https://wovcc.xeniox.uk; "
        "img-src 'self' data: https://maps.googleapis.com https://*.googleapis.com; "
        "frame-src https://www.google.com https://maps.google.com; "
        "object-src 'none';"
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


# ========================================
# Static and Utility Routes
# ========================================

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
    # Cache for 1 year (aggressive caching for images)
    response.cache_control.max_age = 31536000
    response.cache_control.public = True
    return response


@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """Serve uploaded files (event images, etc) from uploads directory"""
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    response = send_from_directory(uploads_dir, filename)
    # Cache for 1 hour (moderate caching for user uploads)
    response.cache_control.max_age = 3600
    response.cache_control.public = True
    return response


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
# Error Handlers
# ========================================

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


# ========================================
# Application Entry Point
# ========================================

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