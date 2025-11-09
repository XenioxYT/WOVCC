"""
WOVCC Flask Application - Page Routes
Handles serving all HTML-rendered pages.

Route authentication/authorization overview:

- `/` (Home): Public
- `/members`: Requires login (shows login form if not authenticated)
- `/matches`: Public
- `/join`: Public
- `/join/activate`: Public (used after payment)
- `/join/cancel`: Public (used after payment cancellation)
- `/admin`: Requires admin authentication
- `/events`: Public
- `/events/<int:event_id>`: Public
"""

from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)

# Page routes
@pages_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@pages_bp.route('/members')
def members():
    """Members page - shows login form or member content based on auth"""
    return render_template('members.html')


@pages_bp.route('/matches')
def matches():
    """Matches page"""
    return render_template('matches.html')


@pages_bp.route('/join')
def join():
    """Join membership page"""
    return render_template('join.html')


@pages_bp.route('/join/activate')
def activate():
    """Account activation page after payment"""
    return render_template('activate.html')


@pages_bp.route('/join/cancel')
def cancel():
    """Payment cancellation page"""
    return render_template('cancel.html')


@pages_bp.route('/admin')
def admin():
    """Admin page - requires authentication"""
    return render_template('admin.html')


@pages_bp.route('/events')
def events():
    """Events page - shows all published events"""
    return render_template('events.html')


@pages_bp.route('/events/<int:event_id>')
def event_detail(event_id):
    """Event detail page"""
    return render_template('event-detail.html', event_id=event_id)