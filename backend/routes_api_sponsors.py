"""
WOVCC Flask Application - Sponsors API Routes
Handles all endpoints for creating, reading, updating, and deleting sponsors.
"""

from flask import Blueprint, jsonify, request
import os
import logging
from datetime import datetime, timezone

from database import get_db, Sponsor
from auth import require_admin
from image_utils import process_and_save_image, delete_image, allowed_file

logger = logging.getLogger(__name__)
sponsors_api_bp = Blueprint('sponsors_api', __name__, url_prefix='/api/sponsors')


# ----- Public Sponsors API -----

@sponsors_api_bp.route('', methods=['GET'])
def get_sponsors():
    """Get all active sponsors (public endpoint)"""
    try:
        db = next(get_db())
        try:
            # Get only active sponsors, ordered by display_order
            sponsors = db.query(Sponsor).filter(
                Sponsor.is_active == True
            ).order_by(Sponsor.display_order.asc(), Sponsor.name.asc()).all()
            
            return jsonify({
                'success': True,
                'sponsors': [s.to_dict() for s in sponsors]
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching sponsors: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ----- Admin Sponsors API -----

@sponsors_api_bp.route('/admin', methods=['GET'])
@require_admin
def get_all_sponsors_admin(user):
    """Get all sponsors with filtering and pagination (admin only)"""
    try:
        search = request.args.get('search', '').strip()
        filter_type = request.args.get('filter', 'all')  # all, active, inactive
        sort_by = request.args.get('sort', 'order')  # order, name, created
        sort_order = request.args.get('order', 'asc')  # asc, desc
        
        db = next(get_db())
        try:
            query = db.query(Sponsor)
            
            # Apply search filter
            if search:
                query = query.filter(
                    Sponsor.name.ilike(f'%{search}%')
                )
            
            # Apply status filter
            if filter_type == 'active':
                query = query.filter(Sponsor.is_active == True)
            elif filter_type == 'inactive':
                query = query.filter(Sponsor.is_active == False)
            
            # Apply sorting
            if sort_by == 'name':
                order_col = Sponsor.name
            elif sort_by == 'created':
                order_col = Sponsor.created_at
            else:  # 'order'
                order_col = Sponsor.display_order
            
            if sort_order == 'desc':
                query = query.order_by(order_col.desc())
            else:
                query = query.order_by(order_col.asc())
            
            # Secondary sort by name for consistency
            if sort_by != 'name':
                query = query.order_by(Sponsor.name.asc())
            
            sponsors = query.all()
            
            return jsonify({
                'success': True,
                'sponsors': [s.to_dict() for s in sponsors],
                'total': len(sponsors)
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching sponsors for admin: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sponsors_api_bp.route('/admin', methods=['POST'])
@require_admin
def create_sponsor(user):
    """Create a new sponsor (admin only)"""
    try:
        # Get form data
        data = request.form.to_dict()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'Sponsor name is required'
            }), 400
        
        # Handle logo upload (required)
        if 'logo' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Sponsor logo is required'
            }), 400
        
        file = request.files['logo']
        if not file or not file.filename:
            return jsonify({
                'success': False,
                'error': 'Sponsor logo is required'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, WebP, SVG'
            }), 400
        
        # Process logo (height-only constraint, no responsive variants for logos)
        upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'sponsors')
        logo_url = process_and_save_image(
            file, 
            upload_folder,
            max_height=80,  # Max 80px height for processing
            create_responsive=False,  # No responsive variants for small logos
            height_only=True  # Scale width proportionally
        )
        
        if not logo_url:
            return jsonify({
                'success': False,
                'error': 'Failed to process logo image'
            }), 400
        
        db = next(get_db())
        try:
            # Get next display order
            max_order = db.query(Sponsor.display_order).order_by(Sponsor.display_order.desc()).first()
            next_order = (max_order[0] + 1) if max_order and max_order[0] is not None else 0
            
            # Create sponsor
            new_sponsor = Sponsor(
                name=data['name'],
                logo_url=logo_url,
                website_url=data.get('website_url', None),
                display_order=int(data.get('display_order', next_order)),
                is_active=data.get('is_active', 'true').lower() == 'true'
            )
            
            db.add(new_sponsor)
            db.commit()
            db.refresh(new_sponsor)
            
            logger.info(f"Sponsor created: {new_sponsor.name} (ID: {new_sponsor.id})")
            
            return jsonify({
                'success': True,
                'message': 'Sponsor created successfully',
                'sponsor': new_sponsor.to_dict()
            }), 201
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error creating sponsor: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sponsors_api_bp.route('/admin/<int:sponsor_id>', methods=['PUT'])
@require_admin
def update_sponsor(user, sponsor_id):
    """Update a sponsor (admin only)"""
    try:
        data = request.form.to_dict()
        
        db = next(get_db())
        try:
            sponsor = db.query(Sponsor).filter(Sponsor.id == sponsor_id).first()
            
            if not sponsor:
                return jsonify({
                    'success': False,
                    'error': 'Sponsor not found'
                }), 404
            
            # Update fields
            if 'name' in data:
                sponsor.name = data['name']
            
            if 'website_url' in data:
                sponsor.website_url = data['website_url'] if data['website_url'] else None
            
            if 'display_order' in data:
                sponsor.display_order = int(data['display_order'])
            
            if 'is_active' in data:
                sponsor.is_active = data['is_active'].lower() == 'true'
            
            # Handle logo replacement
            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename:
                    if not allowed_file(file.filename):
                        return jsonify({
                            'success': False,
                            'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, WebP, SVG'
                        }), 400
                    
                    # Delete old logo
                    if sponsor.logo_url:
                        base_upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
                        delete_image(sponsor.logo_url, base_upload_folder)
                    
                    # Upload new logo
                    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'sponsors')
                    new_logo_url = process_and_save_image(
                        file,
                        upload_folder,
                        max_height=80,
                        create_responsive=False,
                        height_only=True
                    )
                    
                    if not new_logo_url:
                        return jsonify({
                            'success': False,
                            'error': 'Failed to process new logo image'
                        }), 400
                    
                    sponsor.logo_url = new_logo_url
            
            sponsor.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(sponsor)
            
            logger.info(f"Sponsor updated: {sponsor.name} (ID: {sponsor.id})")
            
            return jsonify({
                'success': True,
                'message': 'Sponsor updated successfully',
                'sponsor': sponsor.to_dict()
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error updating sponsor {sponsor_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sponsors_api_bp.route('/admin/<int:sponsor_id>', methods=['DELETE'])
@require_admin
def delete_sponsor(user, sponsor_id):
    """Delete a sponsor (admin only)"""
    try:
        db = next(get_db())
        try:
            sponsor = db.query(Sponsor).filter(Sponsor.id == sponsor_id).first()
            
            if not sponsor:
                return jsonify({
                    'success': False,
                    'error': 'Sponsor not found'
                }), 404
            
            # Delete logo file
            if sponsor.logo_url:
                base_upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
                delete_image(sponsor.logo_url, base_upload_folder)
            
            sponsor_name = sponsor.name
            db.delete(sponsor)
            db.commit()
            
            logger.info(f"Sponsor deleted: {sponsor_name} (ID: {sponsor_id})")
            
            return jsonify({
                'success': True,
                'message': 'Sponsor deleted successfully'
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error deleting sponsor {sponsor_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
