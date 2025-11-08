"""
WOVCC Flask Application - Events API Routes
Handles all endpoints for creating, reading, updating, and deleting events.
"""

from flask import Blueprint, jsonify, request
import os
import logging
from datetime import datetime, timezone

from database import get_db, Event, EventInterest
from auth import require_admin, get_current_user
from image_utils import process_and_save_image, delete_image, allowed_file
from dateutil.relativedelta import relativedelta
from sqlalchemy import or_

logger = logging.getLogger(__name__)
events_api_bp = Blueprint('events_api', __name__, url_prefix='/api/events')


# ----- Events Helper -----

def generate_recurring_events(base_event, db):
    """Generate recurring event instances based on pattern"""
    if not base_event.is_recurring or not base_event.recurrence_pattern:
        return []
    
    generated = []
    current_date = base_event.date
    end_date = base_event.recurrence_end_date
    
    # Limit to 12 occurrences to prevent excessive generation
    max_occurrences = 12
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


@events_api_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get a single event by ID"""
    try:
        db = next(get_db())
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            
            if not event:
                return jsonify({
                    'success': False,
                    'error': 'Event not found'
                }), 404
            
            # Check if event is published (unless admin)
            current_user = get_current_user()
            # Check if event is published (unless admin)
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
                    EventInterest.event_id == event_id,
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
        logger.error(f"Error fetching event {event_id}: {e}")
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
        
        # Parse date
        try:
            event_date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format'
            }), 400
        
        # Handle image upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'events')
                image_url = process_and_save_image(file, upload_folder)
                if not image_url:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to process image'
                    }), 400
        
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
            
            # Create event
            new_event = Event(
                title=data['title'],
                short_description=data['short_description'],
                long_description=data['long_description'],
                date=event_date,
                time=data.get('time', None),
                image_url=image_url,
                location=data.get('location', None),
                category=data.get('category', None),
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
                    db.add(instance)
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
                    event.date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                except:
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
                        except:
                            pass
                    
                    # Delete old recurring instances and regenerate
                    if event.parent_event_id is None:  # Only for parent events
                        db.query(Event).filter(Event.parent_event_id == event.id).delete()
                        db.commit()
                        
                        recurring_instances = generate_recurring_events(event, db)
                        for instance in recurring_instances:
                            db.add(instance)
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
                    new_image_url = process_and_save_image(file, upload_folder)
                    if new_image_url:
                        event.image_url = new_image_url
            
            event.updated_at = datetime.now(timezone.utc)
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


@events_api_bp.route('/<int:event_id>/interest', methods=['POST'])
def toggle_event_interest(event_id):
    """Toggle user interest in an event"""
    try:
        db = next(get_db())
        try:
            event = db.query(Event).filter(Event.id == event_id, Event.is_published == True).first()
            
            if not event:
                return jsonify({
                    'success': False,
                    'error': 'Event not found'
                }), 404
            
            current_user = get_current_user()
            
            if current_user:
                # Check if already interested
                existing = db.query(EventInterest).filter(
                    EventInterest.event_id == event_id,
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
                        event_id=event_id,
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
                    EventInterest.event_id == event_id,
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
                        event_id=event_id,
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
        logger.error(f"Error toggling interest for event {event_id}: {e}")
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