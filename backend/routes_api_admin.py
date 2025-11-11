"""
WOVCC Flask Application - Admin API Routes
Handles all endpoints for the admin panel.
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime, timezone

from database import get_db, User
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
                    'recent_signups': [u.to_dict() for u in recent_signups]
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