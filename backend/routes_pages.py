"""
WOVCC Flask Application - Page Routes
Handles serving all HTML-rendered pages.

Route authentication/authorization overview:

- `/` (Home): Public
- `/login`: Public (login page)
- `/membership`: Requires login (member content)
- `/members`: Legacy page (kept for backwards compatibility)
- `/matches`: Public
- `/join`: Public
- `/join/activate`: Public (used after payment)
- `/join/cancel`: Public (used after payment cancellation)
- `/admin`: Requires admin authentication
- `/events`: Public
- `/events/<int:event_id>`: Public
- `/contact`: Public
 """

from flask import Blueprint, render_template
import os
import logging

logger = logging.getLogger(__name__)
pages_bp = Blueprint('pages', __name__)

# Page routes
@pages_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@pages_bp.route('/members')
def members():
    """Legacy members page - redirects to appropriate page"""
    # This route is kept for backwards compatibility
    # It redirects to login or membership based on context
    return render_template('members.html')


@pages_bp.route('/login')
def login():
    """Login page"""
    return render_template('login.html')


@pages_bp.route('/membership')
def membership():
    """Membership page - requires authentication"""
    return render_template('membership.html')


@pages_bp.route('/matches')
def matches():
    """Matches page with server-side data for SEO"""
    from routes_api_cricket import get_scraped_data
    
    # Get cricket data for SEO
    cricket_data = None
    teams = []
    fixtures_count = 0
    results_count = 0
    
    try:
        data = get_scraped_data()
        teams = data.get('teams', [])
        fixtures_count = len(data.get('fixtures', []))
        results_count = len(data.get('results', []))
        cricket_data = {
            'teams': teams,
            'fixtures_count': fixtures_count,
            'results_count': results_count,
            'last_updated': data.get('last_updated')
        }
    except Exception as e:
        logger.error(f"Error fetching cricket data for SEO: {e}")
    
    return render_template('matches.html', cricket_data=cricket_data, teams=teams)


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
    """Events page - shows all published events with server-side rendered data for SEO"""
    from database import get_db, Event
    from datetime import datetime
    
    upcoming_events = []
    past_events = []
    
    try:
        db = next(get_db())
        try:
            now = datetime.utcnow()
            
            # Get upcoming events (sorted by date ascending - nearest first)
            upcoming = db.query(Event).filter(
                Event.is_published == True,
                Event.date >= now
            ).order_by(Event.date.asc()).all()
            upcoming_events = [e.to_dict() for e in upcoming]
            
            # Get past events (sorted by date descending - most recent first)
            past = db.query(Event).filter(
                Event.is_published == True,
                Event.date < now
            ).order_by(Event.date.desc()).all()
            past_events = [e.to_dict() for e in past]
            
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching events for SEO: {e}")
    
    # Combine for schema.org (all events)
    all_events = upcoming_events + past_events
    
    return render_template(
        'events.html', 
        upcoming_events=upcoming_events,
        past_events=past_events,
        all_events=all_events,
        upcoming_count=len(upcoming_events),
        past_count=len(past_events)
    )


@pages_bp.route('/events/<int:event_id>')
def event_detail(event_id):
    """Event detail page with SEO meta tags"""
    from database import get_db, Event
    
    google_maps_api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    
    # Fetch event data for SEO meta tags (server-side rendering)
    event_data = None
    try:
        db = next(get_db())
        try:
            event = db.query(Event).filter(
                Event.id == event_id,
                Event.is_published == True
            ).first()
            
            if event:
                event_data = {
                    'id': event.id,
                    'title': event.title,
                    'short_description': event.short_description,
                    'long_description': event.long_description,
                    'date': event.date.isoformat() if event.date else None,
                    'date_display': event.date.strftime('%A, %d %B %Y') if event.date else None,
                    'time': event.time,
                    'location': event.location,
                    'category': event.category,
                    'image_url': event.image_url,
                }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching event {event_id} for SEO: {e}")
    
    return render_template(
        'event-detail.html',
        event_id=event_id,
        event=event_data,
        google_maps_api_key=google_maps_api_key
    )


@pages_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')


@pages_bp.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('privacy.html')