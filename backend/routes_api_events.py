"""
WOVCC Flask Application - Events API Routes
Handles all endpoints for creating, reading, updating, and deleting events.
"""

from flask import Blueprint, jsonify, request
import os
import logging
import json
from datetime import datetime, timezone
from openai import OpenAI

from database import get_db, Event, EventInterest
from auth import require_admin, get_current_user
from image_utils import process_and_save_image, delete_image, allowed_file
from slug_utils import generate_event_slug
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
                    image_result = process_and_save_image(file, upload_folder)
                    if image_result:
                        # Extract main URL if dict returned (responsive images), otherwise use string directly
                        event.image_url = image_result['main'] if isinstance(image_result, dict) else image_result
            
            # Regenerate slug if title or date changed (for SEO-friendly URLs)
            if 'title' in data or 'date' in data:
                new_slug = generate_event_slug(event.title, event.date, db, exclude_id=event.id)
                if new_slug:
                    event.slug = new_slug
            
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
        is_recurring = bool(data.get('is_recurring'))
        recurrence_pattern = (data.get('recurrence_pattern') or '').strip() or None
        recurrence_end = (data.get('recurrence_end_date') or '').strip() or None

        # Parse date safely for prompt context (no strict error on failure)
        try:
            parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            human_date = parsed_date.strftime('%A %-d %B %Y %H:%M').replace(' 00:00', '')
        except Exception:
            human_date = date_str

        recurring_text = ''
        if is_recurring and recurrence_pattern:
            if recurrence_end:
                recurring_text = f"This is a recurring event ({recurrence_pattern}) until {recurrence_end}."
            else:
                recurring_text = f"This is a recurring event ({recurrence_pattern}) with no specified end date."
        elif is_recurring:
            recurring_text = "This is a recurring event."

        # Build rich, deterministic prompt with WOVCC context and markdown support info
        system_prompt = (
            "You are an assistant that writes clear, friendly, UK English event descriptions for the "
            "Wickersley Old Village Cricket Club (WOVCC) website. "
            "WOVCC is an ECB Clubmark accredited cricket club based in Wickersley, Rotherham, South Yorkshire, "
            "with its home ground at Northfield Lane, Wickersley, Rotherham, S66 1AL. "
            "The club offers excellent facilities at Northfield Lane, including the main ground, outdoor practice nets "
            "and a clubhouse with bar and function room available for hire. "
            "When writing event descriptions, align them with a welcoming, community-focused club tone, highlight "
            "Long descriptions may be rendered on the website with markdown support (including basic formatting such as "
            "paragraphs, bold, italics and simple lists), but they will be stored and consumed as plain strings in JSON. "
            "Do not include raw HTML tags. "
            "Only respond in British English. "
            "You must respond ONLY with strict JSON and nothing else."
        )

        # Build context about existing content
        existing_context = ""
        if short_existing or long_existing:
            existing_context = "\n\nEXISTING CONTENT TO ENHANCE:"
            if short_existing:
                existing_context += f"\n- Current short description: \"{short_existing}\""
            if long_existing:
                existing_context += f"\n- Current long description: \"{long_existing}\""
            existing_context += (
                "\n\nIMPORTANT: Build upon and improve this existing content. "
                "Maintain the key information and intent but make it more engaging, accurate and well-structured. "
                "If the existing content is already good, keep its core message while refining the language."
            )

        user_prompt = (
            f"EVENT TITLE: {title}\n\n"
            f"EVENT DATE/TIME: {human_date}\n"
            f"{recurring_text}\n"
            f"{existing_context}\n\n"
            f"TASK:\n"
            f"Generate two descriptions for this WOVCC event:\n\n"
            f"1. SHORT DESCRIPTION (1-2 sentences, max 160 characters):\n"
            f"   - Concise teaser for event listings\n"
            f"   - Do not include date/time; focus on what/why\n"
            f"   - Make it engaging and informative\n\n"
            f"2. LONG DESCRIPTION (SUPPORTS MARKDOWN):\n"
            f"   - Fuller description for the event detail page\n"
            f"   - Be welcoming, informative and specific to WOVCC where relevant\n"
            f"   - Include relevant date/time/recurrence context in natural language\n"
            f"   - You may use markdown formatting (paragraphs, **bold**, simple lists)\n"
            f"   - Do not use HTML tags\n"
            f"   - Write in clear UK English\n\n"
            f"OUTPUT FORMAT:\n"
            f"Return ONLY valid JSON with this exact structure:\n"
            f"{{\n"
            f'  "short_description": "your short description here",\n'
            f'  "long_description": "your long description here"\n'
            f"}}\n\n"
            f"No markdown code fences, no extra keys, no explanations."
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