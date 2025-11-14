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
from markupsafe import Markup
import bleach

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
# Initialize CMS Content Snippets
# ========================================
def init_cms_content_if_needed():
    """Initialize CMS content snippets if the table is empty"""
    from database import get_db, ContentSnippet
    
    DEFAULT_SNIPPETS = [
        {
            'key': 'homepage_hero_title',
            'content': 'Welcome to Wickersley Old Village CC',
            'description': 'Homepage hero section - main title'
        },
        {
            'key': 'homepage_hero_subtitle',
            'content': 'A Village cricket club offering ECB Premier League Cricket, Women\'s Cricket & Junior Cricket including Dynamos and All Stars',
            'description': 'Homepage hero section - subtitle/tagline'
        },
        {
            'key': 'homepage_about_p1',
            'content': 'We\'re a Village cricket club offering a variety of cricket from ECB Premier League Cricket, Women\'s Cricket & Junior Cricket including Dynamos and All Stars. We have 3 senior teams playing in the Yorkshire Cricket Southern Premier League in the Championship, Division 1 & Division 5.',
            'description': 'Homepage about section - paragraph 1'
        },
        {
            'key': 'homepage_about_p2',
            'content': 'Our Women\'s section - The Vixens, have 3 teams in the Yorkshire Cricket Premier League competing in Division 1 for Hardball and Softball, and also in Division 3 Softball.',
            'description': 'Homepage about section - paragraph 2'
        },
        {
            'key': 'homepage_about_p3',
            'content': 'We have junior teams in the Ben Jessop Junior Cricket League: U9s, U11s, U13s, U15s, U18s plus our Junior Vixens. Our successful All Stars programme will be back again this year along with Dynamos cricket.',
            'description': 'Homepage about section - paragraph 3'
        },
        {
            'key': 'homepage_about_p4',
            'content': 'Join WOVCC for just £15 (first year) and enjoy drink discounts, member benefits, and access to exclusive content. Renewals are £10/year. Thank you to all our members, guests and sponsors for making each season a great success.',
            'description': 'Homepage about section - paragraph 4'
        },
        {
            'key': 'footer_opening_hours',
            'content': 'Mon-Thu: 4pm-10pm<br>Tue: 4pm-10:30pm<br>Fri: 4pm-11pm<br>Sat: 12pm-11pm<br>Sun: 12pm-10pm',
            'description': 'Footer - Opening hours (supports HTML <br> tags)'
        }
    ]
    
    try:
        db = next(get_db())
        try:
            # Check if content snippets table is empty
            count = db.query(ContentSnippet).count()
            
            if count == 0:
                logger.info("CMS content snippets table is empty. Initializing with default content...")
                
                try:
                    for snippet_data in DEFAULT_SNIPPETS:
                        new_snippet = ContentSnippet(
                            key=snippet_data['key'],
                            content=snippet_data['content'],
                            description=snippet_data['description']
                        )
                        db.add(new_snippet)
                    
                    db.commit()
                    logger.info(f"✅ Initialized {len(DEFAULT_SNIPPETS)} CMS content snippets")
                except Exception as insert_error:
                    db.rollback()
                    # Handle race condition where another worker already inserted
                    if "duplicate" in str(insert_error).lower() or "already exists" in str(insert_error).lower():
                        logger.info("CMS content snippets already initialized by another worker")
                    else:
                        raise
            else:
                logger.info(f"CMS content snippets already initialized ({count} snippets found)")
                
        finally:
            db.close()
    except Exception as e:
        # Don't crash the app if CMS init fails
        if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
            logger.error(f"Error initializing CMS content snippets: {e}")


# Initialize CMS content on startup
init_cms_content_if_needed()


# ========================================
# HTML Sanitization
# ========================================
# Define allowed HTML tags and attributes for CMS content
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'b', 'i', 'u', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    '*': ['class']  # Allow class attribute on all allowed tags
}
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

def sanitize_html(content):
    """Sanitize HTML content to prevent XSS attacks"""
    if not content:
        return ''
    
    # Use bleach to sanitize HTML, allowing only safe tags and attributes
    clean_content = bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True  # Strip disallowed tags rather than escaping them
    )
    
    # Return as Markup so Jinja2 doesn't escape it again
    return Markup(clean_content)


class SafeSnippets(dict):
    """Dictionary wrapper that auto-sanitizes HTML content"""
    def get(self, key, default=''):
        value = super().get(key, default)
        return sanitize_html(value)


# ========================================
# Template Context Processor
# ========================================
@app.context_processor
def inject_snippets():
    """Inject content snippets into all templates with automatic sanitization"""
    from database import get_db, ContentSnippet
    try:
        db = next(get_db())
        try:
            snippets = db.query(ContentSnippet).all()
            snippet_dict = {snippet.key: snippet.content for snippet in snippets}
            return {'snippets': SafeSnippets(snippet_dict)}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error loading content snippets: {e}")
        return {'snippets': SafeSnippets({})}


# Register custom Jinja2 filter for explicit sanitization if needed
@app.template_filter('safe_html')
def safe_html_filter(content):
    """Jinja2 filter to sanitize HTML content"""
    return sanitize_html(content)


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