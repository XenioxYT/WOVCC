# Flask Migration - Proof of Concept

## Branch: `flask-migration`

This branch demonstrates migrating from plain HTML to Flask with Jinja2 templates. The `members.html` page has been converted as a proof-of-concept.

---

## What Changed

### New Files Created

1. **`backend/app.py`** - Flask web application entry point
   - Serves server-side rendered pages using Jinja2 templates
   - Handles static file routing for CSS, JS, and assets
   - Runs on port 5001 (separate from API on port 5000)

2. **`backend/templates/layout.html`** - Base Jinja2 template
   - Contains shared navbar, footer, and newsletter section
   - Other templates extend this to avoid duplication
   - Uses Jinja2 blocks for page-specific content

3. **`backend/templates/members.html`** - Converted members page
   - Extends `layout.html` for shared components
   - Contains only page-specific content in blocks
   - Maintains all original functionality (login, member dashboard, etc.)

### Key Benefits

✅ **Code Reuse**: Navbar and footer are defined once in `layout.html` and shared across all pages  
✅ **Easy Maintenance**: Update shared components in one place  
✅ **Python Integration**: Templates can access backend data, auth state, and database queries  
✅ **Progressive Enhancement**: Existing JavaScript (`auth.js`, `main.js`) still works  
✅ **Incremental Migration**: Convert one page at a time; old static pages can coexist

---

## How to Run

### Start the Flask Web App

```powershell
cd backend
python app.py
```

The app will start on **http://localhost:5001**

### Test the Converted Page

Open your browser to:
- **http://localhost:5001/members** - Converted templated page

### Original API Still Works

The existing `api.py` can run separately on port 5000:

```powershell
cd backend
python api.py
```

---

## Migration Path (Next Steps)

### Option 1: Convert All Pages to Templates

1. Create template versions of remaining pages:
   - `backend/templates/index.html` (home page)
   - `backend/templates/matches.html`
   - `backend/templates/join.html`
   - `backend/templates/admin.html`

2. Each template extends `layout.html` and defines content blocks

3. Update internal links to use Flask routes (`/members` instead of `pages/members.html`)

4. Test each page conversion individually

### Option 2: Merge with Existing API

Combine `app.py` (web pages) and `api.py` (JSON endpoints) into one Flask app:

- Serve templates for browser requests
- Serve JSON for API requests
- Share authentication and database connections
- Single server on one port

### Option 3: Keep Separate (Current Approach)

- `backend/app.py` serves HTML pages (port 5001)
- `backend/api.py` serves JSON API (port 5000)
- Frontend JavaScript calls API endpoints for data
- Good separation of concerns, but requires running two servers

---

## Comparison: Before vs After

### Before (Plain HTML)
```html
<!-- pages/members.html -->
<!DOCTYPE html>
<html>
<head>
  <title>Members</title>
  <link rel="stylesheet" href="../styles/main.css">
</head>
<body>
  <!-- Full navbar copied here -->
  <nav>...</nav>
  
  <!-- Page content -->
  <section>...</section>
  
  <!-- Full footer copied here -->
  <footer>...</footer>
</body>
</html>
```

**Problems:**
- Navbar and footer duplicated in every file
- Changing header requires editing 5+ files
- Hard to integrate server-side auth or data
- No template reuse

### After (Flask + Jinja2)
```html
<!-- backend/templates/members.html -->
{% extends "layout.html" %}

{% block title %}Members Area - WOVCC{% endblock %}

{% block content %}
  <!-- Only page-specific content here -->
  <section>...</section>
{% endblock %}
```

**Benefits:**
- Navbar and footer in `layout.html` (edit once)
- Pages are much shorter and cleaner
- Easy to pass data from Python to template
- Can add server-side logic (auth checks, DB queries, etc.)

---

## Static File Serving

Flask app serves existing static files via custom routes:

- **CSS**: `/styles/main.css` → `styles/main.css`
- **JS**: `/scripts/auth.js` → `scripts/auth.js`
- **Images**: `/assets/logo.png` → `assets/logo.png`

This means:
- No need to move existing `styles/`, `scripts/`, `assets/` folders
- Existing JavaScript continues to work
- Templates reference files with absolute paths (`/styles/main.css`)

---

## Testing the Proof-of-Concept

### ✅ What Works
- Members page renders correctly
- CSS styling applies (navbar, cards, forms)
- JavaScript loads (`auth.js`, `main.js`)
- Login form functionality intact
- Member dashboard displays
- Navigation links work

### 🔄 What's Not Yet Migrated
- Home page (`/`) → still needs template
- Matches page → not converted yet
- Join page → not converted yet
- Admin page → not converted yet

### Next Action: Convert One More Page

Pick another page (e.g., `join.html`) and convert it to prove the pattern is repeatable.

---

## Reverting / Testing Other Approaches

This is on a branch, so you can:
- Test Flask approach safely
- Switch back to `master` if needed: `git checkout master`
- Try other approaches on new branches (SSG, SPA, etc.)

---

## Questions?

- **Do I need to rewrite JavaScript?** No, existing JS works as-is
- **Can I keep using the API?** Yes, Flask templates can call the API or access Python functions directly
- **What about authentication?** Templates can check auth server-side (more secure) or client-side (current approach)
- **Performance?** Server-rendered pages are fast; minimal overhead vs static HTML

---

## Recommendation

✅ **Proceed with Flask migration** if:
- You want to integrate Python backend logic into pages
- You need server-side auth, sessions, or database queries
- You want template reuse and easier maintenance
- You're comfortable with Python

❌ **Consider alternatives** if:
- You want static hosting (JAMstack, CDN)
- You prefer a JavaScript-based framework (React, Vue, Next.js)
- You need very high traffic (SSG + CDN is faster at scale)

For this project (Python backend + moderate traffic + auth/Stripe), **Flask + Jinja2 is the best fit**.
