"""
WOVCC Flask Application - Admin API Routes
Handles all endpoints for the admin panel.
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime, timezone

from database import get_db, User, ContentSnippet, Event, EventInterest
from auth import require_admin
from sqlalchemy import or_, func
from datetime import timedelta
from dateutil import parser

logger = logging.getLogger(__name__)
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')

# ----- Admin User Management API -----

@admin_api_bp.route('/stats', methods=['GET'])
@require_admin
def get_admin_stats(user):
    """Get member statistics for admin dashboard"""
    try:
        db = next(get_db())
        try:
            # Total members
            total_members = db.query(User).filter(User.is_member == True).count()
            
            # Active members (not expired)
            now = datetime.now(timezone.utc)
            active_members = db.query(User).filter(
                User.is_member == True,
                User.payment_status == 'active',
                or_(User.membership_expiry_date.is_(None), User.membership_expiry_date > now)
            ).count()
            
            # Expired members
            expired_members = db.query(User).filter(
                User.is_member == True,
                User.membership_expiry_date < now
            ).count()
            
            # New members this month
            first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            new_members_this_month = db.query(User).filter(
                User.join_date >= first_of_month
            ).count()
            
            # Payment status breakdown
            payment_status_counts = db.query(
                User.payment_status,
                func.count(User.id)
            ).group_by(User.payment_status).all()
            
            payment_status_breakdown = {status: count for status, count in payment_status_counts}
            
            # Newsletter subscribers
            newsletter_subscribers = db.query(User).filter(User.newsletter == True).count()
            
            # Recent signups (last 10)
            recent_signups = db.query(User).order_by(User.created_at.desc()).limit(10).all()
            
            # Members expiring soon (within 30 days)
            thirty_days_from_now = now + timedelta(days=30)
            expiring_soon = db.query(User).filter(
                User.is_member == True,
                User.membership_expiry_date.isnot(None),
                User.membership_expiry_date > now,
                User.membership_expiry_date <= thirty_days_from_now
            ).count()
            
            # Event statistics
            total_events = db.query(Event).count()
            published_events = db.query(Event).filter(Event.is_published == True).count()
            upcoming_events = db.query(Event).filter(
                Event.is_published == True,
                Event.date >= now
            ).count()
            
            # Total event interests
            total_event_interests = db.query(EventInterest).count()
            
            # Most popular event
            most_popular_event = db.query(Event).filter(
                Event.is_published == True
            ).order_by(Event.interested_count.desc()).first()
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_members': total_members,
                    'active_members': active_members,
                    'expired_members': expired_members,
                    'new_members_this_month': new_members_this_month,
                    'newsletter_subscribers': newsletter_subscribers,
                    'expiring_soon': expiring_soon,
                    'payment_status_breakdown': payment_status_breakdown,
                    'recent_signups': [u.to_dict() for u in recent_signups],
                    'total_events': total_events,
                    'published_events': published_events,
                    'upcoming_events': upcoming_events,
                    'total_event_interests': total_event_interests,
                    'most_popular_event': most_popular_event.to_dict() if most_popular_event else None
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_api_bp.route('/users', methods=['GET'])
@require_admin
def get_all_users(user):
    """Get all users with filtering and pagination"""
    try:
        search = request.args.get('search', '').strip()
        filter_type = request.args.get('filter', 'all')
        sort = request.args.get('sort', 'join_date')
        order = request.args.get('order', 'desc')
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid page or per_page parameters.'}), 400
        
        db = next(get_db())
        try:
            query = db.query(User)
            
            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        User.name.ilike(search_term),
                        User.email.ilike(search_term)
                    )
                )
            
            # Apply type filter
            now = datetime.now(timezone.utc)
            if filter_type == 'members':
                query = query.filter(User.is_member == True)
            elif filter_type == 'non-members':
                query = query.filter(User.is_member == False)
            elif filter_type == 'active':
                query = query.filter(
                    User.is_member == True,
                    User.payment_status == 'active',
                    or_(User.membership_expiry_date.is_(None), User.membership_expiry_date > now)
                )
            elif filter_type == 'expired':
                query = query.filter(
                    User.is_member == True,
                    User.membership_expiry_date < now
                )
            elif filter_type == 'admins':
                query = query.filter(User.is_admin == True)
            
            # Apply sorting
            if sort == 'name':
                query = query.order_by(User.name.desc() if order == 'desc' else User.name.asc())
            elif sort == 'email':
                query = query.order_by(User.email.desc() if order == 'desc' else User.email.asc())
            elif sort == 'join_date':
                query = query.order_by(User.join_date.desc() if order == 'desc' else User.join_date.asc())
            elif sort == 'expiry_date':
                query = query.order_by(User.membership_expiry_date.desc() if order == 'desc' else User.membership_expiry_date.asc())
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            users = query.offset(offset).limit(per_page).all()
            
            return jsonify({
                'success': True,
                'users': [u.to_dict(include_sensitive=True) for u in users],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_api_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(admin_user, user_id):
    """Update user details (admin only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Update fields
            if 'name' in data:
                user.name = data['name']
            if 'email' in data:
                # Check if email is already taken
                existing = db.query(User).filter(User.email == data['email'], User.id != user_id).first()
                if existing:
                    return jsonify({
                        'success': False,
                        'error': 'Email already in use'
                    }), 400
                user.email = data['email']
            if 'is_member' in data:
                user.is_member = data['is_member']
            if 'is_admin' in data:
                user.is_admin = data['is_admin']
            if 'newsletter' in data:
                user.newsletter = data['newsletter']
            if 'payment_status' in data:
                user.payment_status = data['payment_status']
            if 'membership_tier' in data:
                user.membership_tier = data['membership_tier']
            if 'membership_expiry_date' in data:
                if data['membership_expiry_date']:
                    user.membership_expiry_date = parser.parse(data['membership_expiry_date'])
                else:
                    user.membership_expiry_date = None
            
            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            
            return jsonify({
                'success': True,
                'message': 'User updated successfully',
                'user': user.to_dict(include_sensitive=True)
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_api_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(admin_user, user_id):
    """Delete a user (admin only)"""
    try:
        # Prevent deleting yourself
        if admin_user.id == user_id:
            return jsonify({
                'success': False,
                'error': 'Cannot delete your own account'
            }), 400
        
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            db.delete(user)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ----- Content Management API -----

@admin_api_bp.route('/content', methods=['GET'])
@require_admin
def get_all_content_snippets(user):
    """Get all content snippets (admin only)"""
    try:
        db = next(get_db())
        try:
            snippets = db.query(ContentSnippet).all()
            
            return jsonify({
                'success': True,
                'snippets': [s.to_dict() for s in snippets]
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching content snippets: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_api_bp.route('/content/<string:key>', methods=['GET'])
@require_admin
def get_content_snippet(user, key):
    """Get a specific content snippet (admin only)"""
    try:
        db = next(get_db())
        try:
            snippet = db.query(ContentSnippet).filter(ContentSnippet.key == key).first()
            
            if not snippet:
                return jsonify({
                    'success': False,
                    'error': 'Content snippet not found'
                }), 404
            
            return jsonify({
                'success': True,
                'snippet': snippet.to_dict()
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching content snippet {key}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_api_bp.route('/content/<string:key>', methods=['PUT'])
@require_admin
def update_content_snippet(admin_user, key):
    """Update a content snippet (admin only)"""
    try:
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Content is required'
            }), 400
        
        db = next(get_db())
        try:
            snippet = db.query(ContentSnippet).filter(ContentSnippet.key == key).first()
            
            if not snippet:
                return jsonify({
                    'success': False,
                    'error': 'Content snippet not found'
                }), 404
            
            # Update content
            snippet.content = data['content']
            if 'description' in data:
                snippet.description = data['description']
            snippet.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(snippet)
            
            return jsonify({
                'success': True,
                'message': 'Content snippet updated successfully',
                'snippet': snippet.to_dict()
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error updating content snippet {key}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ----- AI Help Assistant -----

@admin_api_bp.route('/help/chat', methods=['POST'])
@require_admin
def ai_help_chat(user):
    """AI Help assistant for admin panel (admin only)"""
    import os
    from openai import OpenAI
    
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        user_message = data['message']
        conversation_history = data.get('history', [])
        
        # Check if OpenAI API key is configured
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not openai_api_key:
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured'
            }), 500
        
        # Initialize OpenAI client
        openai_base_url = os.environ.get('OPENAI_BASE_URL')
        if openai_base_url:
            client = OpenAI(api_key=openai_api_key, base_url=openai_base_url)
        else:
            client = OpenAI(api_key=openai_api_key)
        model = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        # System context about the admin panel
        system_context = """You are a helpful AI assistant for the WOVCC (Wickersley Old Village Cricket Club) website admin panel. 
Your role is to help administrators understand and use the various features available to them. Keep your answers simple and do not use technical language.

**Admin Panel Features:**

1. **Live Matches Tab**
   - Purpose: Control live match display on the homepage
   - Features:
     * Toggle live section on/off (shows/hides live match info on homepage)
     * Select which match is currently being played
     * Add optional external livestream URL (e.g., YouTube)
     * Play-Cricket widgets automatically display for all today's matches
   - How to use:
     1. Turn on the live toggle
     2. Select the current match from the dropdown
     3. Optionally add a livestream URL
     4. Click "Save Configuration"

2. **User Management Tab**
   - Purpose: Manage all registered users and memberships
   - Features:
     * View all users with filtering (all, members, active, expired, admins, non-members)
     * Search users by name or email
     * Edit user details (name, email, membership tier, payment status, expiry date)
     * Toggle user flags (is_member, is_admin, newsletter)
     * Delete users (cannot delete yourself)
   - User Fields:
     * Name, Email (required)
     * Membership Tier: Annual Member, Social Member, Junior Member, Honorary Member
     * Payment Status: pending, active, expired, cancelled
     * Membership Expiry Date
     * Is Member (boolean)
     * Is Admin (boolean)
     * Newsletter Subscriber (boolean)
   - Statistics displayed:
     * Total members, Active members, Expired members
     * New members this month, Newsletter subscribers
     * Expiring soon (within 30 days)

3. **Events Tab**
   - Purpose: Create and manage club events
   - Features:
     * Create new events with full details
     * Edit existing events
     * Delete events
     * View interested users for each event
     * Publish/unpublish events
     * Create recurring events (daily, weekly, monthly)
     * AI-powered description generation
   - Event Fields:
     * Title (required)
     * Short Description (required, max 255 chars)
     * Long Description (required, Markdown supported)
     * Date (required)
     * Time (optional)
     * Location (optional)
     * Category (optional, e.g., Training, Social, Match Day, Fundraiser)
     * Image upload (PNG, JPG, WebP, max 5MB - auto-optimized)
     * Published status (boolean)
   - Recurring Events:
     * Pattern: daily, weekly, monthly
     * End date required
     * Generates up to 12 occurrences
     * Each occurrence is a separate event linked to parent

4. **Content Tab (CMS)**
   - Purpose: Edit website text content without touching code
   - Features:
     * Edit homepage hero title and subtitle
     * Edit 4 paragraphs in the "About" section
     * Edit footer opening hours
     * Changes appear immediately on the site
   - Available Snippets:
     * homepage_hero_title - Main welcome message
     * homepage_hero_subtitle - Tagline under title
     * homepage_about_p1 - First about paragraph
     * homepage_about_p2 - Women's section info
     * homepage_about_p3 - Junior teams info
     * homepage_about_p4 - Membership info
     * footer_opening_hours - Opening hours (HTML <br> tags supported)
   - How to edit:
     1. Click edit icon next to snippet
     2. Modify text in textarea
     3. Use basic HTML if needed (<br>, <strong>, <em>)
     4. Click "Update Content"

**General Admin Panel Info:**
- Access: Must be logged in as an admin user
- Navigation: Tabs at top to switch between sections
- Authentication: All changes require admin privileges
- Auto-save: No auto-save - always click save/update buttons
- Permissions: Only admins can access this panel

**Common Questions:**
- "How do I add a new admin?" - Edit user in User Management tab, check "Is Admin" box
- "How do I show a live match?" - Go to Live Matches tab, toggle on, select match, save
- "How do I change homepage text?" - Go to Content tab, edit the relevant snippet
- "How do I create an event?" - Go to Events tab, click "Create Event", fill form
- "Where are opening hours?" - Content tab, edit "footer_opening_hours" snippet

Answer questions clearly and concisely. If asked about features not listed here, politely say you don't have information about that feature."""

        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": system_context}
        ]
        
        # Add conversation history (limit to last 10 messages to avoid token limits)
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message.content
        
        return jsonify({
            'success': True,
            'message': assistant_message,
            'tokens_used': response.usage.total_tokens
        })
        
    except Exception as e:
        logger.error(f"Error in AI help chat: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get AI response: {str(e)}'
        }), 500