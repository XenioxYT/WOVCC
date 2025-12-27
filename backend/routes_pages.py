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
def event_detail_by_id(event_id):
    """
    Legacy route: Redirect numeric event IDs to SEO-friendly slug URLs.
    This preserves backward compatibility for old links and helps Google update its index.
    """
    from flask import redirect, url_for
    from database import get_db, Event
    
    try:
        db = next(get_db())
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            
            if event and event.slug:
                # 301 permanent redirect to slug URL (tells Google the new URL is canonical)
                return redirect(url_for('pages.event_detail', event_slug=event.slug), code=301)
            elif event:
                # Event exists but no slug yet - render page directly
                return _render_event_detail(event, event_id)
            else:
                # Event not found - return 404
                return render_template('event-detail.html', event_id=event_id, event=None, google_maps_api_key=''), 404
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in event redirect for ID {event_id}: {e}")
        return render_template('event-detail.html', event_id=event_id, event=None, google_maps_api_key=''), 404


@pages_bp.route('/events/<event_slug>')
def event_detail(event_slug):
    """
    Primary route: SEO-friendly event detail page with slug URLs.
    Example: /events/christmas-party-dec-2024
    """
    from database import get_db, Event
    
    google_maps_api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    
    try:
        db = next(get_db())
        try:
            # Look up by slug
            event = db.query(Event).filter(
                Event.slug == event_slug,
                Event.is_published == True
            ).first()
            
            if event:
                return _render_event_detail(event, event.id, google_maps_api_key)
            else:
                # Event not found
                return render_template(
                    'event-detail.html',
                    event_id=None,
                    event=None,
                    google_maps_api_key=google_maps_api_key
                ), 404
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching event by slug '{event_slug}' for SEO: {e}")
        return render_template(
            'event-detail.html',
            event_id=None,
            event=None,
            google_maps_api_key=google_maps_api_key
        ), 404


def _render_event_detail(event, event_id, google_maps_api_key=''):
    """Helper function to render event detail page with SEO data."""
    event_data = {
        'id': event.id,
        'slug': event.slug,
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
    
    if not google_maps_api_key:
        google_maps_api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    
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