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
import hashlib
import glob
from markupsafe import Markup
import bleach
from urllib.parse import urlparse

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


# ========================================
# Cache Busting for Static Assets
# ========================================
def _generate_asset_version():
    """
    Generate a version hash based on the modification times of all static files.
    This ensures browsers fetch fresh copies when any CSS/JS file changes.
    """
    backend_dir = os.path.dirname(__file__)
    styles_dir = os.path.join(backend_dir, '..', 'styles')
    scripts_dir = os.path.join(backend_dir, '..', 'scripts')
    assets_dir = os.path.join(backend_dir, '..', 'assets')
    
    # Collect modification times from all static files
    mtimes = []
    for directory in [styles_dir, scripts_dir, assets_dir]:
        if os.path.exists(directory):
            for pattern in ['*.css', '*.js', '*.webp', '*.png', '*.jpg', '*.svg']:
                for filepath in glob.glob(os.path.join(directory, pattern)):
                    try:
                        mtimes.append(str(os.path.getmtime(filepath)))
                    except OSError:
                        pass
    
    # Create a hash from all modification times
    if mtimes:
        hash_input = ''.join(sorted(mtimes))
        return hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    # Fallback to current timestamp if no files found
    return str(int(datetime.now().timestamp()))[:8]


# Generate the asset version at startup (cached for the lifetime of the worker)
ASSET_VERSION = _generate_asset_version()
logger.info(f"Asset version (cache busting): {ASSET_VERSION}")


def _normalize_url(value):
    """Strip trailing slash while keeping scheme/host"""
    if not value:
        return ''
    return value.rstrip('/')


def _split_env_list(value):
    """Split comma-separated env values into a cleaned list"""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def _origin_from_url(url_value):
    """Extract origin (scheme://host[:port]) from a URL string"""
    if not url_value:
        return None
    parsed = urlparse(url_value)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _get_www_variant(url_value):
    """Return www. variant of a URL if applicable"""
    parsed = urlparse(url_value)
    if parsed.hostname and not parsed.hostname.startswith('www.'):
        port = f":{parsed.port}" if parsed.port else ''
        return f"{parsed.scheme}://www.{parsed.hostname}{port}"
    return None


# Base URLs (configurable via .env)
# Default points at the club's canonical domain; override in production via backend/.env.
SITE_BASE_URL = _normalize_url(os.environ.get('SITE_BASE_URL', 'https://wickersleycricket.com'))


def _resolve_api_base_url():
    """
    Determine API base URL from env.
    Default to a relative path (`/api`) so the frontend calls the same origin, avoiding CORS
    issues between www/non-www hostnames and simplifying deployments behind a reverse proxy.
    """
    env_api = _normalize_url(os.environ.get('API_BASE_URL', ''))
    if env_api:
        return env_api
    return '/api'


API_BASE_URL = _resolve_api_base_url()


def _build_cors_origins():
    """Build the CORS origins list from env with sensible defaults."""
    env_origins = _split_env_list(os.environ.get('CORS_ORIGINS', ''))
    if env_origins:
        return [_normalize_url(origin) for origin in env_origins]
    
    origins = ['http://localhost:5000', 'http://127.0.0.1:5000']
    # Production defaults (www + non-www). Override with CORS_ORIGINS for other domains.
    origins.extend(['https://wickersleycricket.com', 'https://www.wickersleycricket.com'])
    if SITE_BASE_URL:
        origins.append(SITE_BASE_URL)
        www_variant = _get_www_variant(SITE_BASE_URL)
        if www_variant:
            origins.append(www_variant)
    return origins

# Enable CORS with credentials support for httpOnly cookies
CORS(app, supports_credentials=True, origins=_build_cors_origins())

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
            'content': 'Monday: 4pm – 10pm<br>Tuesday: 4pm – 10:30pm<br>Wednesday: 4pm – 10pm<br>Thursday: 4pm – 10pm<br>Friday: 4pm – 11pm<br>Saturday: 12 noon – 11pm<br>Sunday: 12 noon – 10pm',
            'description': 'Footer - Opening hours (supports HTML <br> tags)'
        },
        {
            'key': 'footer_visit_info',
            'content': 'Free parking on site.',
            'description': 'Footer - Visitor info / travel notes (supports basic HTML)'
        },
        {
            'key': 'footer_christmas_hours',
            'content': '',
            'description': 'Footer - Christmas opening hours (leave blank to hide)'
        },
        {
            'key': 'footer_new_year_hours',
            'content': '',
            'description': 'Footer - New Year opening hours (leave blank to hide)'
        },
        {
            'key': 'homepage_functions_title',
            'content': 'Host Your Event at the Clubhouse',
            'description': 'Homepage - Private functions section title'
        },
        {
            'key': 'homepage_functions_text',
            'content': 'Looking for a venue for your next celebration? A section of our clubhouse can be reserved for private functions. With a licensed bar, ample parking, DJ facilities available, and a welcoming atmosphere, WOVCC is the perfect venue for birthday parties, wakes and special occasions. <a href="/contact" style="color: white; text-decoration: underline;">Contact us for details.</a>',
            'description': 'Homepage - Private functions section text (supports HTML). Mention venue features, pricing, etc.'
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
                # Backfill any newly added default snippets that don't yet exist
                existing_keys = {row[0] for row in db.query(ContentSnippet.key).all()}
                missing_snippets = [s for s in DEFAULT_SNIPPETS if s['key'] not in existing_keys]
                if missing_snippets:
                    logger.info(f"Adding {len(missing_snippets)} missing CMS snippets...")
                    try:
                        for snippet_data in missing_snippets:
                            db.add(ContentSnippet(
                                key=snippet_data['key'],
                                content=snippet_data['content'],
                                description=snippet_data['description']
                            ))
                        db.commit()
                        logger.info("✅ Missing CMS snippets added")
                    except Exception as insert_error:
                        db.rollback()
                        if "duplicate" in str(insert_error).lower() or "already exists" in str(insert_error).lower():
                            logger.info("CMS snippets already added by another worker")
                        else:
                            raise
                
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


@app.context_processor
def inject_app_config():
    """Inject application configuration into all templates for JavaScript usage"""
    # PUBLIC API base used by browser JS:
    # Prefer same-origin `/api` to avoid CORS (especially www vs non-www).
    # - If you truly serve the frontend separately from the API, set PUBLIC_API_BASE_URL explicitly.
    public_api_raw = os.environ.get('PUBLIC_API_BASE_URL', '').strip()
    if public_api_raw:
        api_base_url = _normalize_url(public_api_raw)
    else:
        # If API_BASE_URL points to the same origin as the current request, it's safe to expose.
        env_api_raw = os.environ.get('API_BASE_URL', '').strip()
        env_api_origin = _origin_from_url(env_api_raw)
        current_origin = _origin_from_url(request.url_root)
        if env_api_raw and (env_api_raw.startswith('/') or (env_api_origin and env_api_origin == current_origin)):
            api_base_url = _normalize_url(env_api_raw)
        else:
            api_base_url = '/api'
    
    return {
        'app_config': {
            'api_base_url': api_base_url,
            'site_base_url': SITE_BASE_URL,
            'is_debug': DEBUG,
            'environment': os.environ.get('ENVIRONMENT', 'development' if DEBUG else 'production'),
            'google_maps_api_key': os.environ.get('GOOGLE_MAPS_API_KEY', '')
        },
        'site_base_url': SITE_BASE_URL,
        'asset_version': ASSET_VERSION
    }


@app.context_processor
def inject_sponsors():
    """Inject active sponsors into all templates"""
    from database import get_db, Sponsor
    try:
        db = next(get_db())
        try:
            sponsors = db.query(Sponsor).filter(
                Sponsor.is_active == True
            ).order_by(Sponsor.display_order.asc(), Sponsor.name.asc()).all()
            return {'sponsors': [s.to_dict() for s in sponsors]}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error loading sponsors: {e}")
        return {'sponsors': []}


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
from routes_api_sponsors import sponsors_api_bp

app.register_blueprint(pages_bp)
app.register_blueprint(cricket_api_bp)
app.register_blueprint(auth_api_bp)
app.register_blueprint(admin_api_bp)
app.register_blueprint(events_api_bp)
app.register_blueprint(webhooks_api_bp)
app.register_blueprint(contact_bp)
app.register_blueprint(sponsors_api_bp)


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
    # Content-Security-Policy:
    # - No inline scripts allowed (all scripts must be external files)
    # - Allow external marked.js CDN
    # - Permit inline styles via 'unsafe-inline' (styles are less risky than scripts)
    # IMPORTANT:
    # - Allow API calls to your Cloudflare-tunnelled backend and external API hostname.
    # - Keep localhost targets for local/dev usage.
    # - Keep cdn.jsdelivr.net for external scripts.
    # - Update this if you introduce new domains.
    connect_sources = ["'self'", "http://localhost:5000", "http://127.0.0.1:5000"]
    api_origin = _origin_from_url(API_BASE_URL)
    site_origin = _origin_from_url(SITE_BASE_URL)
    if api_origin:
        connect_sources.append(api_origin)
    if site_origin:
        connect_sources.append(site_origin)
    # Deduplicate while preserving order
    connect_sources = list(dict.fromkeys(connect_sources))

    csp = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://www.play-cricket.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://www.play-cricket.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        f"connect-src {' '.join(connect_sources)}; "
        "img-src 'self' data: https://maps.googleapis.com https://*.googleapis.com https://www.play-cricket.com https://s3-eu-west-1.amazonaws.com; "
        "frame-src https://www.google.com https://maps.google.com https://www.youtube.com https://player.vimeo.com; "
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
    # Cache for 1 year (aggressive caching safe because we use versioned URLs ?v=...)
    response.cache_control.max_age = 31536000
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
    # Use SITE_BASE_URL for consistent canonical URLs
    base_url = SITE_BASE_URL or request.url_root.rstrip('/')
    return """User-agent: *
Allow: /

# Allow public API endpoints needed for page rendering
Allow: /api/events
Allow: /api/events/
Allow: /api/data
Allow: /api/sponsors
Allow: /api/content
Allow: /api/cricket
Allow: /api/health

# Block sensitive API endpoints
Disallow: /api/auth/
Disallow: /api/admin/
Disallow: /api/webhooks/
Disallow: /api/contact

# Block private pages
Disallow: /admin
Disallow: /login
Disallow: /membership
Disallow: /members
Disallow: /join/activate
Disallow: /join/cancel

Sitemap: {}/sitemap.xml
""".format(base_url), 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/sitemap.xml')
def sitemap():
    """Dynamic XML sitemap for search engines (Google Search Console compatible)"""
    from database import get_db, Event
    from datetime import datetime, timezone
    
    # Use SITE_BASE_URL for consistent canonical URLs
    base_url = SITE_BASE_URL or request.url_root.rstrip('/')
    
    # Static pages with their priorities and change frequencies
    static_pages = [
        {'url': '/', 'priority': '1.0', 'changefreq': 'daily'},
        {'url': '/events', 'priority': '0.9', 'changefreq': 'daily'},
        {'url': '/matches', 'priority': '0.8', 'changefreq': 'daily'},
        {'url': '/join', 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': '/contact', 'priority': '0.6', 'changefreq': 'monthly'},
        {'url': '/privacy', 'priority': '0.3', 'changefreq': 'yearly'},
    ]
    
    # Build XML
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    
    # Current timestamp for static pages
    now_dt = datetime.now(timezone.utc)
    now = now_dt.strftime('%Y-%m-%d')
    
    # Add static pages
    for page in static_pages:
        xml_parts.append('  <url>')
        xml_parts.append(f'    <loc>{base_url}{page["url"]}</loc>')
        xml_parts.append(f'    <lastmod>{now}</lastmod>')
        xml_parts.append(f'    <changefreq>{page["changefreq"]}</changefreq>')
        xml_parts.append(f'    <priority>{page["priority"]}</priority>')
        xml_parts.append('  </url>')
    
    # Add dynamic event pages
    try:
        db = next(get_db())
        try:
            # Get all published events (both upcoming and past for SEO)
            events = db.query(Event).filter(Event.is_published == True).all()
            logger.info(f"Sitemap: Found {len(events)} published events")
            
            for event in events:
                try:
                    # Use updated_at or created_at for lastmod
                    lastmod = event.updated_at or event.created_at
                    lastmod_str = lastmod.strftime('%Y-%m-%d') if lastmod else now
                    
                    # Determine priority based on whether event is upcoming
                    # Handle timezone-naive dates safely
                    event_date = event.date
                    is_upcoming = False
                    if event_date:
                        # Make comparison timezone-safe
                        if event_date.tzinfo is None:
                            # Naive datetime - compare with naive
                            is_upcoming = event_date > datetime.utcnow()
                        else:
                            # Aware datetime - compare with aware
                            is_upcoming = event_date > now_dt
                    
                    priority = '0.7' if is_upcoming else '0.5'
                    
                    # Use SEO-friendly slug URL if available, otherwise fall back to ID
                    event_url = f"{base_url}/events/{event.slug}" if event.slug else f"{base_url}/events/{event.id}"
                    
                    xml_parts.append('  <url>')
                    xml_parts.append(f'    <loc>{event_url}</loc>')
                    xml_parts.append(f'    <lastmod>{lastmod_str}</lastmod>')
                    xml_parts.append(f'    <changefreq>daily</changefreq>')
                    xml_parts.append(f'    <priority>{priority}</priority>')
                    xml_parts.append('  </url>')
                except Exception as event_error:
                    logger.error(f"Error processing event {event.id} for sitemap: {event_error}")
                    continue
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching events for sitemap: {e}", exc_info=True)
    
    xml_parts.append('</urlset>')
    
    xml_content = '\n'.join(xml_parts)
    
    response = app.response_class(
        response=xml_content,
        status=200,
        mimetype='application/xml'
    )
    # Allow caching for 1 hour
    response.cache_control.max_age = 3600
    response.cache_control.public = True
    return response


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