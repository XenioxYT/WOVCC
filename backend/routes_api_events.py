"""
WOVCC Flask Application - Events API Routes
Handles all endpoints for creating, reading, updating, and deleting events.
"""

from flask import Blueprint, jsonify, request
import os
import logging
import json
import requests as http_requests  # Avoid conflict with Flask's request
from datetime import datetime, timezone
from openai import OpenAI

from database import get_db, Event, EventInterest
from auth import require_admin, get_current_user
from image_utils import process_and_save_image, delete_image, allowed_file
from slug_utils import generate_event_slug
from football_image_generator import generate_match_graphic, fetch_team_badge, SPORTSDB_API_BASE
from dateutil.relativedelta import relativedelta
from sqlalchemy import or_

logger = logging.getLogger(__name__)
events_api_bp = Blueprint('events_api', __name__, url_prefix='/api/events')


# ----- Events Helper -----

def generate_recurring_events(base_event, db):
    """Generate recurring event instances based on pattern until end date"""
    if not base_event.is_recurring or not base_event.recurrence_pattern:
        return []
    
    if not base_event.recurrence_end_date:
        return []
    
    generated = []
    current_date = base_event.date
    end_date = base_event.recurrence_end_date
    
    # Safety limit to prevent runaway loops (max 1 year of daily events)
    max_occurrences = 365
    count = 0
    
    while current_date <= end_date and count < max_occurrences:
        # Skip the first occurrence (it's the base event)
        if count > 0:
            new_event = Event(
                title=base_event.title,
                short_description=base_event.short_description,
                long_description=base_event.long_description,
                date=current_date,
                time=base_event.time,
                image_url=base_event.image_url,
                location=base_event.location,
                category=base_event.category,
                is_recurring=False,  # Generated instances are not recurring themselves
                recurrence_pattern=None,
                recurrence_end_date=None,
                parent_event_id=base_event.id,
                is_published=base_event.is_published,
                created_by_user_id=base_event.created_by_user_id
            )
            generated.append(new_event)
        
        # Calculate next occurrence
        if base_event.recurrence_pattern == 'daily':
            current_date = current_date + relativedelta(days=1)
        elif base_event.recurrence_pattern == 'weekly':
            current_date = current_date + relativedelta(weeks=1)
        elif base_event.recurrence_pattern == 'monthly':
            current_date = current_date + relativedelta(months=1)
        
        count += 1
    
    return generated


def find_event_by_identifier(db, identifier):
    """Find an event by ID (if numeric) or slug (if string)."""
    if str(identifier).isdigit():
        return db.query(Event).filter(Event.id == int(identifier)).first()
    else:
        return db.query(Event).filter(Event.slug == identifier).first()

# ----- Events API -----

@events_api_bp.route('', methods=['GET'])
def get_events():
    """Get all published events (or all for admins)"""
    try:
        show_all = request.args.get('show_all', 'false').lower() == 'true'
        filter_type = request.args.get('filter', 'upcoming')
        category = request.args.get('category', None)
        search = request.args.get('search', None)
        
        db = next(get_db())
        try:
            query = db.query(Event)
            
            # Admin-only: show unpublished events
            if show_all:
                current_user = get_current_user()
                if not current_user or not current_user.is_admin:
                    query = query.filter(Event.is_published == True)
            else:
                query = query.filter(Event.is_published == True)
            
            # Date filtering
            now = datetime.now(timezone.utc)
            if filter_type == 'upcoming':
                query = query.filter(Event.date >= now)
                query = query.order_by(Event.date.asc())
            elif filter_type == 'past':
                query = query.filter(Event.date < now)
                query = query.order_by(Event.date.desc())
            else:  # 'all'
                query = query.order_by(Event.date.desc())
            
            # Category filter
            if category and category != 'all':
                query = query.filter(Event.category == category)
            
            # Search
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        Event.title.ilike(search_term),
                        Event.short_description.ilike(search_term),
                        Event.long_description.ilike(search_term)
                    )
                )
            
            events = query.all()
            
            resp = jsonify({
                'success': True,
                'events': [e.to_dict() for e in events],
                'count': len(events)
            })
            
            return resp
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@events_api_bp.route('/<event_identifier>', methods=['GET'])
def get_event(event_identifier):
    """Get a single event by ID or slug"""
    try:
        db = next(get_db())
        try:
            # Check if identifier is numeric (ID) or string (slug)
            if event_identifier.isdigit():
                event = db.query(Event).filter(Event.id == int(event_identifier)).first()
            else:
                event = db.query(Event).filter(Event.slug == event_identifier).first()
            
            if not event:
                return jsonify({
                    'success': False,
                    'error': 'Event not found'
                }), 404
            
            # Check if event is published (unless admin)
            current_user = get_current_user()
            if not event.is_published:
                if not current_user or not current_user.is_admin:
                    return jsonify({
                        'success': False,
                        'error': 'Event not found'
                    }), 404
            
            # Check if user has expressed interest
            user_interested = False
            if current_user:
                interest = db.query(EventInterest).filter(
                    EventInterest.event_id == event.id,
                    EventInterest.user_id == current_user.id
                ).first()
                user_interested = interest is not None
            
            event_data = event.to_dict()
            event_data['user_interested'] = user_interested
            
            resp = jsonify({
                'success': True,
                'event': event_data
            })
            
            return resp
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching event {event_identifier}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@events_api_bp.route('', methods=['POST'])
@require_admin
def create_event(user):
    """Create a new event (admin only)"""
    try:
        # Get form data
        data = request.form.to_dict()
        
        # Validate required fields
        if not data.get('title') or not data.get('short_description') or not data.get('long_description') or not data.get('date'):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: title, short_description, long_description, date'
            }), 400
        
        # Parse date (now expects just a date, not datetime)
        try:
            # Handle both date-only (YYYY-MM-DD) and datetime formats for backward compatibility
            date_str = data['date']
            if 'T' in date_str or ' ' in date_str:
                # Old datetime format
                event_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # New date-only format - set time to midnight UTC
                event_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': f'Invalid date format: {str(e)}'
            }), 400
        
        # Handle image upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'events')
                image_result = process_and_save_image(file, upload_folder)
                if not image_result:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to process image'
                    }), 400
                # Extract main URL if dict returned (responsive images), otherwise use string directly
                image_url = image_result['main'] if isinstance(image_result, dict) else image_result
        
        db = next(get_db())
        try:
            # Parse recurring settings
            is_recurring = data.get('is_recurring', 'false').lower() == 'true'
            recurrence_pattern = data.get('recurrence_pattern', None) if is_recurring else None
            recurrence_end_date = None
            
            if is_recurring and data.get('recurrence_end_date'):
                try:
                    recurrence_end_date = datetime.fromisoformat(data['recurrence_end_date'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Invalid recurrence_end_date format'}), 400
            
            # Handle football match fields
            is_football_match = data.get('is_football_match', 'false').lower() == 'true'
            home_team = None
            away_team = None
            football_competition = None
            
            if is_football_match:
                home_team = data.get('home_team', '').strip()
                away_team = data.get('away_team', '').strip()
                football_competition = data.get('football_competition', '').strip()
                
                if not home_team or not away_team:
                    return jsonify({
                        'success': False,
                        'error': 'Football matches require home_team and away_team'
                    }), 400
                
                # Validate teams exist in TheSportsDB
                for team_name, team_label in [(home_team, 'Home team'), (away_team, 'Away team')]:
                    try:
                        url = f"{SPORTSDB_API_BASE}/searchteams.php?t={team_name}"
                        response = http_requests.get(url, timeout=10)
                        response.raise_for_status()
                        api_data = response.json()
                        
                        if not api_data.get('teams'):
                            return jsonify({
                                'success': False,
                                'error': f"{team_label} '{team_name}' not found in sports database"
                            }), 400
                        
                        # Check if it's a soccer team
                        soccer_teams = [t for t in api_data['teams'] if t.get('strSport', '').lower() == 'soccer']
                        if not soccer_teams:
                            return jsonify({
                                'success': False,
                                'error': f"{team_label} '{team_name}' is not a soccer team. Found: {api_data['teams'][0].get('strSport')}"
                            }), 400
                    except http_requests.RequestException as e:
                        logger.warning(f"Could not validate team {team_name}: {e}")
                        # Continue anyway - don't block event creation if API is down
                
                # Generate football image if no image was uploaded
                if not image_url:
                    try:
                        # Format date for display
                        match_date_display = event_date.strftime('%a %d %b').upper()
                        match_time_display = data.get('time', '').upper() or 'TBC'
                        
                        upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'events')
                        generated_image_path = generate_match_graphic(
                            home_team=home_team,
                            away_team=away_team,
                            competition=football_competition or 'Football',
                            match_date=match_date_display,
                            match_time=match_time_display,
                            output_path=os.path.join(upload_folder, f"football_{home_team.lower().replace(' ', '_')}_vs_{away_team.lower().replace(' ', '_')}_{event_date.strftime('%Y%m%d')}.webp")
                        )
                        # Convert absolute path to relative URL
                        if generated_image_path:
                            image_url = '/uploads/events/' + os.path.basename(generated_image_path)
                            logger.info(f"Generated football match image: {image_url}")
                    except Exception as e:
                        logger.error(f"Error generating football image: {e}")
                        # Continue without image - don't fail event creation
            
            # Generate SEO-friendly slug from title and date
            event_slug = generate_event_slug(data['title'], event_date, db)
            
            # Create event
            new_event = Event(
                slug=event_slug,
                title=data['title'],
                short_description=data['short_description'],
                long_description=data['long_description'],
                date=event_date,
                time=data.get('time', None),
                image_url=image_url,
                location=data.get('location', None),
                category=data.get('category', None),
                is_football_match=is_football_match,
                home_team=home_team,
                away_team=away_team,
                football_competition=football_competition,
                is_recurring=is_recurring,
                recurrence_pattern=recurrence_pattern,
                recurrence_end_date=recurrence_end_date,
                is_published=data.get('is_published', 'false').lower() == 'true',
                created_by_user_id=user.id
            )
            
            db.add(new_event)
            db.commit()
            db.refresh(new_event)
            
            # Generate recurring instances if applicable
            if is_recurring and recurrence_pattern and recurrence_end_date:
                recurring_instances = generate_recurring_events(new_event, db)
                for instance in recurring_instances:
                    # Generate unique slug for each recurring instance
                    instance.slug = generate_event_slug(instance.title, instance.date, db)
                    db.add(instance)
                    # Flush after each add so the slug is visible in subsequent queries
                    db.flush()
                db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Event created successfully',
                'event': new_event.to_dict(include_sensitive=True)
            }), 201
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@events_api_bp.route('/<int:event_id>', methods=['PUT'])
@require_admin
def update_event(user, event_id):
    """Update an event (admin only)"""
    try:
        data = request.form.to_dict()
        
        db = next(get_db())
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            
            if not event:
                return jsonify({
                    'success': False,
                    'error': 'Event not found'
                }), 404
            
            # Update fields if provided
            if 'title' in data:
                event.title = data['title']
            if 'short_description' in data:
                event.short_description = data['short_description']
            if 'long_description' in data:
                event.long_description = data['long_description']
            if 'date' in data:
                try:
                    # Handle both date-only (YYYY-MM-DD) and datetime formats for backward compatibility
                    date_str = data['date']
                    if 'T' in date_str or ' ' in date_str:
                        # Old datetime format
                        event.date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        # New date-only format - set time to midnight UTC
                        event.date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            if 'time' in data:
                event.time = data['time']
            if 'location' in data:
                event.location = data['location']
            if 'category' in data:
                event.category = data['category']
            if 'is_published' in data:
                event.is_published = data['is_published'].lower() == 'true'
            
            # Handle recurring event updates
            if 'is_recurring' in data:
                is_recurring = data['is_recurring'].lower() == 'true'
                event.is_recurring = is_recurring
                
                if is_recurring:
                    if 'recurrence_pattern' in data:
                        event.recurrence_pattern = data['recurrence_pattern']
                    if 'recurrence_end_date' in data:
                        try:
                            event.recurrence_end_date = datetime.fromisoformat(data['recurrence_end_date'].replace('Z', '+00:00'))
                        except ValueError:
                            pass
                    
                    # Delete old recurring instances and regenerate
                    if event.parent_event_id is None:  # Only for parent events
                        db.query(Event).filter(Event.parent_event_id == event.id).delete()
                        db.commit()
                        
                        recurring_instances = generate_recurring_events(event, db)
                        for instance in recurring_instances:
                            # Generate unique slug for each recurring instance
                            instance.slug = generate_event_slug(instance.title, instance.date, db)
                            db.add(instance)
                            # Flush after each add so the slug is visible in subsequent queries
                            db.flush()
                else:
                    event.recurrence_pattern = None
                    event.recurrence_end_date = None
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    # Delete old image
                    if event.image_url:
                        upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
                        delete_image(event.image_url, upload_folder)
                    
                    # Upload new image
                    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'events')
                    image_result = process_and_save_image(file, upload_folder)
                    if image_result:
                        # Extract main URL if dict returned (responsive images), otherwise use string directly
                        event.image_url = image_result['main'] if isinstance(image_result, dict) else image_result
            
            # Handle football match updates
            if 'is_football_match' in data:
                is_football_match = data['is_football_match'].lower() == 'true'
                event.is_football_match = is_football_match
                
                if is_football_match:
                    home_team = data.get('home_team', '').strip() or event.home_team
                    away_team = data.get('away_team', '').strip() or event.away_team
                    football_competition = data.get('football_competition', '').strip() or event.football_competition
                    
                    if not home_team or not away_team:
                        return jsonify({
                            'success': False,
                            'error': 'Football matches require home_team and away_team'
                        }), 400
                    
                    # Check if teams changed - regenerate image
                    teams_changed = (home_team != event.home_team or away_team != event.away_team)
                    
                    event.home_team = home_team
                    event.away_team = away_team
                    event.football_competition = football_competition
                    
                    # Regenerate football image if teams changed and no new image was uploaded
                    if teams_changed and 'image' not in request.files:
                        try:
                            # Delete old generated image if it exists
                            if event.image_url and 'football_' in event.image_url:
                                upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
                                delete_image(event.image_url, upload_folder)
                            
                            match_date_display = event.date.strftime('%a %d %b').upper()
                            match_time_display = (event.time or '').upper() or 'TBC'
                            
                            upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'events')
                            generated_image_path = generate_match_graphic(
                                home_team=home_team,
                                away_team=away_team,
                                competition=football_competition or 'Football',
                                match_date=match_date_display,
                                match_time=match_time_display,
                                output_path=os.path.join(upload_folder, f"football_{home_team.lower().replace(' ', '_')}_vs_{away_team.lower().replace(' ', '_')}_{event.date.strftime('%Y%m%d')}.webp")
                            )
                            if generated_image_path:
                                event.image_url = '/uploads/events/' + os.path.basename(generated_image_path)
                                logger.info(f"Regenerated football match image: {event.image_url}")
                        except Exception as e:
                            logger.error(f"Error regenerating football image: {e}")
                else:
                    # Clearing football fields if switched off
                    event.home_team = None
                    event.away_team = None
                    event.football_competition = None
            elif event.is_football_match:
                # Update individual fields if event is already a football match
                if 'home_team' in data:
                    event.home_team = data['home_team'].strip()
                if 'away_team' in data:
                    event.away_team = data['away_team'].strip()
                if 'football_competition' in data:
                    event.football_competition = data['football_competition'].strip()
            
            # Regenerate slug if title or date changed (for SEO-friendly URLs)
            if 'title' in data or 'date' in data:
                new_slug = generate_event_slug(event.title, event.date, db, exclude_id=event.id)
                if new_slug:
                    event.slug = new_slug
            
            event.updated_at = datetime.now(timezone.utc)
            
            # Cascade updates to child instances if this is a parent recurring event
            # Note: We don't cascade if is_recurring was just changed (handled above by regeneration)
            if event.is_recurring and event.parent_event_id is None and 'is_recurring' not in data:
                # Get all child instances
                child_events = db.query(Event).filter(Event.parent_event_id == event.id).all()
                
                # Fields to cascade from parent to children
                cascade_fields = []
                if 'title' in data:
                    cascade_fields.append(('title', event.title))
                if 'short_description' in data:
                    cascade_fields.append(('short_description', event.short_description))
                if 'long_description' in data:
                    cascade_fields.append(('long_description', event.long_description))
                if 'time' in data:
                    cascade_fields.append(('time', event.time))
                if 'location' in data:
                    cascade_fields.append(('location', event.location))
                if 'category' in data:
                    cascade_fields.append(('category', event.category))
                if 'is_published' in data:
                    cascade_fields.append(('is_published', event.is_published))
                
                # Handle image cascade
                image_changed = 'image' in request.files
                if image_changed:
                    cascade_fields.append(('image_url', event.image_url))
                
                # Apply cascaded updates to all children
                if cascade_fields:
                    for child in child_events:
                        for field_name, field_value in cascade_fields:
                            setattr(child, field_name, field_value)
                        
                        # Regenerate slug if title changed
                        if 'title' in data:
                            child.slug = generate_event_slug(child.title, child.date, db, exclude_id=child.id)
                        
                        child.updated_at = datetime.now(timezone.utc)
                    
                    logger.info(f"Cascaded updates to {len(child_events)} child instances of event {event.id}")
            
            db.commit()
            db.refresh(event)
            
            return jsonify({
                'success': True,
                'message': 'Event updated successfully',
                'event': event.to_dict(include_sensitive=True)
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@events_api_bp.route('/<int:event_id>', methods=['DELETE'])
@require_admin
def delete_event(user, event_id):
    """Delete an event (admin only)"""
    try:
        db = next(get_db())
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            
            if not event:
                return jsonify({
                    'success': False,
                    'error': 'Event not found'
                }), 404
            
            # Delete image if exists
            if event.image_url:
                upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
                delete_image(event.image_url, upload_folder)
            
            # Delete recurring instances if this is a parent event
            if event.parent_event_id is None and event.is_recurring:
                db.query(Event).filter(Event.parent_event_id == event.id).delete()
            
            # Delete event interests
            db.query(EventInterest).filter(EventInterest.event_id == event.id).delete()
            
            # Delete event
            db.delete(event)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Event deleted successfully'
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@events_api_bp.route('/<event_identifier>/interest', methods=['POST'])
def toggle_event_interest(event_identifier):
    """Toggle user interest in an event (accepts ID or slug)"""
    try:
        db = next(get_db())
        try:
            event = find_event_by_identifier(db, event_identifier)
            
            if not event or not event.is_published:
                return jsonify({
                    'success': False,
                    'error': 'Event not found'
                }), 404
            
            current_user = get_current_user()
            
            if current_user:
                # Check if already interested
                existing = db.query(EventInterest).filter(
                    EventInterest.event_id == event.id,
                    EventInterest.user_id == current_user.id
                ).first()
                
                if existing:
                    # Remove interest
                    db.delete(existing)
                    event.interested_count = max(0, event.interested_count - 1)
                    action = 'removed'
                else:
                    # Add interest
                    interest = EventInterest(
                        event_id=event.id,
                        user_id=current_user.id
                    )
                    db.add(interest)
                    event.interested_count += 1
                    action = 'added'
            else:
                # For non-logged-in users, get email from request
                data = request.get_json() or {}
                email = data.get('email')
                name = data.get('name')
                
                if not email:
                    return jsonify({
                        'success': False,
                        'error': 'Email required for non-members'
                    }), 400
                
                # Check if already interested by email
                existing = db.query(EventInterest).filter(
                    EventInterest.event_id == event.id,
                    EventInterest.user_email == email
                ).first()
                
                if existing:
                    # Remove interest
                    db.delete(existing)
                    event.interested_count = max(0, event.interested_count - 1)
                    action = 'removed'
                else:
                    # Add interest
                    interest = EventInterest(
                        event_id=event.id,
                        user_id=None,
                        user_email=email,
                        user_name=name
                    )
                    db.add(interest)
                    event.interested_count += 1
                    action = 'added'
            
            db.commit()
            db.refresh(event)
            
            return jsonify({
                'success': True,
                'action': action,
                'interested_count': event.interested_count
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error toggling interest for event {event_identifier}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@events_api_bp.route('/<int:event_id>/interested-users', methods=['GET'])
@require_admin
def get_interested_users(user, event_id):
    """Get list of users interested in an event (admin only)"""
    try:
        db = next(get_db())
        try:
            # Use ORM relationships
            event = db.query(Event).filter(Event.id == event_id).first()
            
            if not event:
                return jsonify({
                    'success': False,
                    'error': 'Event not found'
                }), 404
            
            users_list = []
            for interest in event.interests:
                if interest.user:
                    # Member interest (has associated user account)
                    users_list.append({
                        'name': interest.user.name,
                        'email': interest.user.email,
                        'is_member': True,
                        'created_at': interest.created_at.isoformat()
                    })
                else:
                    # Non-member interest (anonymous)
                    users_list.append({
                        'name': interest.user_name or 'Anonymous',
                        'email': interest.user_email,
                        'is_member': False,
                        'created_at': interest.created_at.isoformat()
                    })
            
            return jsonify({
                'success': True,
                'count': len(users_list),
                'users': users_list
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching interested users for event {event_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@events_api_bp.route('/categories', methods=['GET'])
def get_event_categories():
    """Get all unique event categories"""
    try:
        db = next(get_db())
        try:
            categories = db.query(Event.category).filter(
                Event.category.isnot(None),
                Event.is_published == True
            ).distinct().all()
            
            category_list = [c[0] for c in categories if c[0]]
            
            return jsonify({
                'success': True,
                'categories': sorted(category_list)
            })
            
        finally:
            db.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@events_api_bp.route('/validate-team', methods=['POST'])
@require_admin
def validate_football_team(user):
    """
    Validate a football team name against TheSportsDB.
    Returns team info if found, or error with suggestions if not.
    
    Expects JSON:
    {
        "team_name": "Arsenal"
    }
    
    Returns:
    {
        "success": true,
        "found": true,
        "team": {
            "name": "Arsenal",
            "league": "English Premier League",
            "badge_url": "..."
        }
    }
    or
    {
        "success": true,
        "found": false,
        "error": "Team 'Arsenall' not found as a soccer team",
        "suggestions": ["Arsenal", "Arsenal Tula"]
    }
    """
    try:
        data = request.get_json() or {}
        team_name = (data.get('team_name') or '').strip()
        
        if not team_name:
            return jsonify({
                'success': False,
                'error': 'team_name is required'
            }), 400
        
        # Search TheSportsDB
        url = f"{SPORTSDB_API_BASE}/searchteams.php?t={team_name}"
        response = http_requests.get(url, timeout=10)
        response.raise_for_status()
        
        api_data = response.json()
        
        if not api_data.get('teams'):
            return jsonify({
                'success': True,
                'found': False,
                'error': f"No team found matching '{team_name}'",
                'suggestions': []
            })
        
        # Find soccer teams
        soccer_teams = [t for t in api_data['teams'] if t.get('strSport', '').lower() == 'soccer']
        
        if not soccer_teams:
            # No soccer teams, but found other sports - return suggestions
            other_teams = [t.get('strTeam') for t in api_data['teams'][:5]]
            return jsonify({
                'success': True,
                'found': False,
                'error': f"'{team_name}' was found but is not a soccer team. Found: {api_data['teams'][0].get('strSport')}",
                'suggestions': other_teams
            })
        
        # Found soccer team(s)
        team = soccer_teams[0]
        return jsonify({
            'success': True,
            'found': True,
            'team': {
                'name': team.get('strTeam'),
                'league': team.get('strLeague'),
                'badge_url': team.get('strBadge') or team.get('strLogo'),
                'country': team.get('strCountry')
            }
        })
        
    except http_requests.RequestException as e:
        logger.error(f"Error validating team: {e}")
        return jsonify({
            'success': False,
            'error': f'Error contacting sports database: {str(e)}'
        }), 502
    except Exception as e:
        logger.error(f"Error validating team: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@events_api_bp.route('/ai-descriptions', methods=['POST'])
@require_admin
def generate_event_descriptions_ai(user):
    """
    Generate short and long descriptions for an event using OpenAI (or compatible) API.

    Expects JSON:
    {
        "title": "Event title",
        "short_description": "Existing short (optional)",
        "long_description": "Existing long (optional)",
        "date": "2025-06-10T18:00",
        "is_recurring": true/false,
        "recurrence_pattern": "daily|weekly|monthly|null",
        "recurrence_end_date": "2025-08-10" (optional)
    }

    Returns JSON:
    {
        "success": true,
        "result": {
            "short_description": "...",
            "long_description": "..."
        }
    }
    """
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        date_str = (data.get('date') or '').strip()

        if not title or not date_str:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: title and date'
            }), 400

        short_existing = (data.get('short_description') or '').strip()
        long_existing = (data.get('long_description') or '').strip()
        time_str = (data.get('time') or '').strip()
        location = (data.get('location') or '').strip()
        category = (data.get('category') or '').strip()
        is_recurring = bool(data.get('is_recurring'))
        recurrence_pattern = (data.get('recurrence_pattern') or '').strip() or None
        recurrence_end = (data.get('recurrence_end_date') or '').strip() or None
        
        # Football match fields
        is_football_match = bool(data.get('is_football_match'))
        home_team = (data.get('home_team') or '').strip()
        away_team = (data.get('away_team') or '').strip()
        football_competition = (data.get('football_competition') or '').strip()

        # Parse date safely for prompt context (no strict error on failure)
        try:
            parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            human_date = parsed_date.strftime('%A %-d %B %Y')
        except Exception:
            human_date = date_str

        # Build event details section with all available information
        event_details = []
        event_details.append(f"Date: {human_date}")
        if time_str:
            event_details.append(f"Time: {time_str}")
        if location:
            event_details.append(f"Location: {location}")
        if category:
            event_details.append(f"Category: {category}")
        
        # Football match details
        football_context = ''
        if is_football_match and home_team and away_team:
            football_context = f"\n\nFOOTBALL MATCH DETAILS:\n"
            football_context += f"- Home Team: {home_team}\n"
            football_context += f"- Away Team: {away_team}\n"
            if football_competition:
                football_context += f"- Competition: {football_competition}\n"
            football_context += "This is a football/soccer watch event at the clubhouse."
        
        recurring_text = ''
        if is_recurring and recurrence_pattern:
            if recurrence_end:
                recurring_text = f"Recurrence: This is a recurring event ({recurrence_pattern}) until {recurrence_end}."
            else:
                recurring_text = f"Recurrence: This is a recurring event ({recurrence_pattern}) with no specified end date."
        elif is_recurring:
            recurring_text = "Recurrence: This is a recurring event."

        # Engaging but factual prompt
        system_prompt = (
            "You are a copywriter creating event descriptions for Wickersley Old Village Cricket Club (WOVCC), "
            "a community cricket club in Wickersley, Rotherham, South Yorkshire. The clubhouse is at Northfield Lane.\n\n"
            "STYLE:\n"
            "- Write engaging, well-written descriptions in British English\n"
            "- Use a warm, friendly tone\n"
            "- Use markdown formatting (bold, bullet points where helpful)\n"
            "- Make it enjoyable to read\n\n"
            "IMPORTANT - DO NOT INVENT DETAILS:\n"
            "- Do NOT make up specific details the user hasn't provided\n"
            "- For example: don't invent how many quiz rounds there are, what food is served, what the atmosphere is like, or specific features of an event\n"
            "- If you only have basic info (title, time, place), write a good general description without padding it with made-up specifics\n"
            "- You CAN mention that drinks are available at the bar (this is always true)\n\n"
            "AVOID:\n"
            "- Pushy promotional phrases like 'Join us!', 'Don't miss!', 'See you there!', 'All welcome!'\n\n"
            "Respond with valid JSON only."
        )

        # Build context about existing content
        existing_context = ""
        if short_existing or long_existing:
            existing_context = "\n\nEXISTING CONTENT TO REFINE:"
            if short_existing:
                existing_context += f"\n- Current short description: \"{short_existing}\""
            if long_existing:
                existing_context += f"\n- Current long description: \"{long_existing}\""
            existing_context += (
                "\n\nIMPORTANT: Build upon this existing content but make it more factual and less promotional. "
                "Remove any salesy or call-to-action language. Keep the core information."
            )

        user_prompt = (
            f"EVENT: {title}\n\n"
            f"DETAILS:\n"
            f"{chr(10).join('- ' + d for d in event_details)}\n"
            f"{('- ' + recurring_text) if recurring_text else ''}\n"
            f"{football_context}\n"
            f"{existing_context}\n\n"
            f"Write two descriptions:\n\n"
            f"1. SHORT DESCRIPTION: An engaging one-line summary (don't include date/time).\n\n"
            f"2. LONG DESCRIPTION: A well-written description for the event page. "
            f"Include the key details (when, where) naturally in the text. "
            f"Use markdown formatting. "
            f"Don't invent specific details that weren't provided above.\n\n"
            f"Output as JSON: {{\"short_description\": \"...\", \"long_description\": \"...\"}}"
        )
        
        openai_api_key = os.getenv('OPENAI_API_KEY')
        openai_base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        openai_model = os.getenv('OPENAI_MODEL')

        if not openai_api_key:
            return jsonify({
                'success': False,
                'error': 'AI generation not configured on server (missing API key)'
            }), 500

        # Initialize OpenAI client
        client = OpenAI(
            api_key=openai_api_key,
            base_url=openai_base_url
        )

        try:
            completion = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.6,
            )
        except Exception as e:
            logger.error(f"Error calling AI API: {e}")
            return jsonify({
                'success': False,
                'error': f'Error contacting AI generation service: {str(e)}'
            }), 502

        # Extract content from response
        content = completion.choices[0].message.content
        
        if not content:
            logger.error("AI API returned empty content")
            return jsonify({
                'success': False,
                'error': 'AI response was empty'
            }), 502
        
        logger.info(f"AI Content received: {content[:100]}...")  # Log first 100 chars

        try:
            parsed = json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse AI JSON content: {e}; content={content!r}")
            return jsonify({
                'success': False,
                'error': 'AI response was not valid JSON'
            }), 502

        short_generated = (parsed.get('short_description') or '').strip()
        long_generated = (parsed.get('long_description') or '').strip()

        if not short_generated and not long_generated:
            return jsonify({
                'success': False,
                'error': 'AI response missing descriptions'
            }), 502

        return jsonify({
            'success': True,
            'result': {
                'short_description': short_generated,
                'long_description': long_generated
            }
        })

    except Exception as e:
        logger.error(f"Error generating AI event descriptions: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error while generating descriptions'
        }), 500