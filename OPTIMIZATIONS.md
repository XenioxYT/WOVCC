# Flask Migration - Recommended Optimizations

## 🎯 High Priority Optimizations

### 1. **Add Flask Caching** ⚡
The `/api/data` endpoint loads from a JSON file every time. Add Flask-Caching to cache this in memory.

**Benefits:**
- Faster page loads (especially for matches page)
- Reduced file I/O
- Better scalability

**Implementation:**
```python
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes
})

@app.route('/api/data', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_all_data():
    # existing code...
```

### 2. **Add Security Headers** 🔒
Flask doesn't add security headers by default. Add them to protect against common vulnerabilities.

**Benefits:**
- Protection against XSS, clickjacking, MIME-sniffing
- Better security score
- Industry best practice

**Implementation:**
```python
from flask_talisman import Talisman

# In production only
if not DEBUG:
    Talisman(app, 
        content_security_policy=None,  # Configure based on your needs
        force_https=True
    )

# Or manually add headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

### 3. **Add Static File Caching Headers** 📦
Tell browsers to cache CSS/JS/images for better performance.

**Implementation:**
```python
@app.route('/styles/<path:filename>')
def serve_styles(filename):
    """Serve CSS files from styles directory"""
    styles_dir = os.path.join(os.path.dirname(__file__), '..', 'styles')
    response = send_from_directory(styles_dir, filename)
    response.cache_control.max_age = 31536000  # 1 year
    response.cache_control.public = True
    return response
```

### 4. **Add Compression** 🗜️
Compress responses to reduce bandwidth and improve load times.

**Implementation:**
```python
from flask_compress import Compress

Compress(app)
```

### 5. **Environment-specific Error Handlers** 🐛
Return HTML error pages for browser requests, JSON for API requests.

**Current Issue:** 404/500 always returns JSON, even for page requests.

**Implementation:**
```python
@app.errorhandler(404)
def not_found(e):
    # Check if request expects JSON
    if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
        return jsonify({
            'success': False,
            'error': 'Endpoint not found'
        }), 404
    # Return HTML error page for browser requests
    return render_template('404.html'), 404
```

---

## 🎨 Medium Priority Improvements

### 6. **Server-Side Data Injection for SEO** 🔍
Pass initial data to templates for better SEO and faster first paint.

**Example for index page:**
```python
@app.route('/')
def index():
    """Home page with pre-loaded fixtures"""
    try:
        # Load next 3 fixtures for quick display
        fixtures = scraper.get_team_fixtures(None)[:3]
        has_live_matches = scraper.check_matches_today()
    except:
        fixtures = []
        has_live_matches = False
    
    return render_template('index.html', 
                         fixtures=fixtures,
                         has_live_matches=has_live_matches)
```

Then in template:
```html
<script>
  // Pre-loaded data available immediately
  window.initialFixtures = {{ fixtures | tojson }};
  window.hasLiveMatches = {{ has_live_matches | tojson }};
</script>
```

### 7. **Add Meta Tags for Social Sharing** 📱
Add Open Graph and Twitter Card meta tags to layout.html.

**Benefits:**
- Better social media previews
- Professional appearance
- More engagement

**Implementation in layout.html:**
```html
<!-- Open Graph -->
<meta property="og:title" content="{% block og_title %}{{ self.title() }}{% endblock %}">
<meta property="og:description" content="{% block og_description %}{{ self.description() }}{% endblock %}">
<meta property="og:image" content="{{ url_for('serve_assets', filename='logo.png', _external=True) }}">
<meta property="og:url" content="{{ request.url }}">
<meta property="og:type" content="website">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@wickersleyovcc">
```

### 8. **Add Sitemap.xml** 🗺️
Generate a sitemap for better SEO.

**Implementation:**
```python
@app.route('/sitemap.xml')
def sitemap():
    """Generate sitemap.xml"""
    pages = []
    # Static pages
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and not rule.rule.startswith('/api/'):
            pages.append({
                'loc': request.url_root.rstrip('/') + rule.rule,
                'lastmod': datetime.now().strftime('%Y-%m-%d'),
                'changefreq': 'weekly',
                'priority': 0.8
            })
    
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response
```

### 9. **Add Robots.txt** 🤖
```python
@app.route('/robots.txt')
def robots():
    """Robots.txt file"""
    return """User-agent: *
Allow: /
Sitemap: {}/sitemap.xml
""".format(request.url_root.rstrip('/')), 200, {'Content-Type': 'text/plain'}
```

### 10. **Add Rate Limiting** 🚦
Protect API endpoints from abuse.

**Implementation:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # existing code...
```

---

## 🔧 Code Quality Improvements

### 11. **Add Request ID Logging** 📝
Track requests across logs for debugging.

**Implementation:**
```python
import uuid

@app.before_request
def before_request():
    request.id = str(uuid.uuid4())
    logger.info(f"[{request.id}] {request.method} {request.path}")
```

### 12. **Use Blueprints for Better Organization** 📂
Split routes into logical blueprints.

**Structure:**
```
backend/
  routes/
    __init__.py
    pages.py      # Page routes
    api.py        # API routes
    auth.py       # Auth routes
    payments.py   # Payment routes
```

### 13. **Add Health Check Details** 💊
Enhance health check to verify database and API connectivity.

**Implementation:**
```python
@app.route('/api/health')
def health():
    """Enhanced health check"""
    health_status = {
        'status': 'ok',
        'service': 'WOVCC Application',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat()
    }
    
    # Check database
    try:
        db = next(get_db())
        db.execute('SELECT 1')
        health_status['database'] = 'ok'
    except:
        health_status['database'] = 'error'
        health_status['status'] = 'degraded'
    
    # Check scraper data
    try:
        teams = scraper.get_teams()
        health_status['scraper'] = 'ok' if teams else 'no_data'
    except:
        health_status['scraper'] = 'error'
        health_status['status'] = 'degraded'
    
    return jsonify(health_status)
```

### 14. **Add Request Validation** ✅
Use Flask-Inputs or marshmallow for request validation.

### 15. **Add API Versioning** 🔢
Future-proof the API with versioning.

**Example:**
```python
@app.route('/api/v1/teams')
def get_teams_v1():
    # Version 1 implementation
```

---

## 🚀 Performance Optimizations

### 16. **Use Production WSGI Server** 🏭
**Never use Flask development server in production!**

**Recommended: Gunicorn or uWSGI**

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**Or with uWSGI:**
```bash
pip install uwsgi
uwsgi --http :5000 --wsgi-file app.py --callable app --master --processes 4
```

### 17. **Add Database Connection Pooling** 💾
If using SQLAlchemy, configure connection pooling.

### 18. **Implement Lazy Loading for Images** 🖼️
Add `loading="lazy"` to images in templates.

**Example in layout.html:**
```html
<img src="/assets/logo.png" alt="WOVCC Logo" loading="lazy">
```

### 19. **Minify CSS/JS in Production** 📦
Use Flask-Assets to minify and bundle assets.

### 20. **Add Service Worker for Offline Support** 📴
Make the site work offline with a service worker.

---

## 🔐 Security Enhancements

### 21. **Add CSRF Protection** 🛡️
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
```

### 22. **Implement Content Security Policy** 🔒
Restrict what resources can be loaded.

### 23. **Add Input Sanitization** 🧹
Sanitize user inputs to prevent XSS attacks.

### 24. **Use Environment Variables for Secrets** 🔑
Already doing this! But ensure `.env` is in `.gitignore`.

### 25. **Add Helmet-like Headers** ⛑️
Already mentioned, but critical for production.

---

## 📊 Monitoring & Analytics

### 26. **Add Application Monitoring** 📈
Use Sentry or similar for error tracking.

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn="your-sentry-dsn",
        integrations=[FlaskIntegration()],
    )
```

### 27. **Add Performance Monitoring** ⏱️
Track request times and slow queries.

### 28. **Add Google Analytics or Matomo** 📊
Track user behavior (already present in client-side code).

---

## 🎯 Quick Wins (Can Implement Now)

1. **Add compression** - 1 line of code
2. **Add caching headers to static files** - 3 lines per route
3. **Add robots.txt** - 5 lines of code
4. **Add lazy loading to images** - Add attribute to existing `<img>` tags
5. **Fix 404 handler to return HTML for page requests** - 10 lines of code

---

## 📝 Notes

- Most optimizations can be added incrementally
- Test each optimization in development before production
- Monitor performance impact after each change
- Some optimizations (like Blueprints) are architectural and can wait

**Priority Order:**
1. Security headers (production safety)
2. Caching (performance)
3. Compression (performance)
4. Error pages (user experience)
5. Everything else based on need
