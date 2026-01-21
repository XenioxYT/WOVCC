"""
WOVCC Flask Application - Beer Images API Routes
Handles all endpoints for creating, reading, updating, and deleting beer images for homepage carousel.
"""

from flask import Blueprint, jsonify, request
import os
import logging
from datetime import datetime, timezone

from database import get_db, BeerImage
from auth import require_admin
from image_utils import process_and_save_image, delete_image, allowed_file

logger = logging.getLogger(__name__)
beer_images_api_bp = Blueprint('beer_images_api', __name__, url_prefix='/api/beer-images')


# ----- Public Beer Images API -----

@beer_images_api_bp.route('', methods=['GET'])
def get_beer_images():
    """Get all active beer images (public endpoint)"""
    try:
        db = next(get_db())
        try:
            # Get only active beer images, ordered by display_order
            beer_images = db.query(BeerImage).filter(
                BeerImage.is_active == True
            ).order_by(BeerImage.display_order.asc(), BeerImage.name.asc()).all()
            
            return jsonify({
                'success': True,
                'beer_images': [img.to_dict() for img in beer_images]
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching beer images: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ----- Admin Beer Images API -----

@beer_images_api_bp.route('/admin', methods=['GET'])
@require_admin
def get_all_beer_images_admin(user):
    """Get all beer images with filtering (admin only)"""
    try:
        search = request.args.get('search', '').strip()
        filter_type = request.args.get('filter', 'all')  # all, active, inactive
        sort_by = request.args.get('sort', 'order')  # order, name, created
        sort_order = request.args.get('order', 'asc')  # asc, desc
        
        db = next(get_db())
        try:
            query = db.query(BeerImage)
            
            # Apply search filter
            if search:
                query = query.filter(
                    BeerImage.name.ilike(f'%{search}%')
                )
            
            # Apply status filter
            if filter_type == 'active':
                query = query.filter(BeerImage.is_active == True)
            elif filter_type == 'inactive':
                query = query.filter(BeerImage.is_active == False)
            
            # Apply sorting
            if sort_by == 'name':
                order_col = BeerImage.name
            elif sort_by == 'created':
                order_col = BeerImage.created_at
            else:  # 'order'
                order_col = BeerImage.display_order
            
            if sort_order == 'desc':
                query = query.order_by(order_col.desc())
            else:
                query = query.order_by(order_col.asc())
            
            # Secondary sort by name for consistency
            if sort_by != 'name':
                query = query.order_by(BeerImage.name.asc())
            
            beer_images = query.all()
            
            return jsonify({
                'success': True,
                'beer_images': [img.to_dict() for img in beer_images],
                'total': len(beer_images)
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error fetching beer images for admin: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@beer_images_api_bp.route('/admin', methods=['POST'])
@require_admin
def create_beer_image(user):
    """Create a new beer image (admin only)"""
    try:
        # Get form data
        data = request.form.to_dict()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'Beer image name is required'
            }), 400
        
        # Handle image upload (required)
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Beer image is required'
            }), 400
        
        file = request.files['image']
        if not file or not file.filename:
            return jsonify({
                'success': False,
                'error': 'Beer image is required'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, WebP'
            }), 400
        
        # Process image (larger size for carousel display)
        upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'beer-images')
        image_url = process_and_save_image(
            file, 
            upload_folder,
            max_width=800,  # Good size for carousel
            max_height=600,
            create_responsive=False
        )
        
        if not image_url:
            return jsonify({
                'success': False,
                'error': 'Failed to process image'
            }), 400
        
        db = next(get_db())
        try:
            # Get next display order
            max_order = db.query(BeerImage.display_order).order_by(BeerImage.display_order.desc()).first()
            next_order = (max_order[0] + 1) if max_order and max_order[0] is not None else 0
            
            # Create beer image
            new_image = BeerImage(
                name=data['name'],
                image_url=image_url,
                display_order=int(data.get('display_order', next_order)),
                is_active=data.get('is_active', 'true').lower() == 'true'
            )
            
            db.add(new_image)
            db.commit()
            db.refresh(new_image)
            
            logger.info(f"Beer image created: {new_image.name} (ID: {new_image.id})")
            
            return jsonify({
                'success': True,
                'message': 'Beer image created successfully',
                'beer_image': new_image.to_dict()
            }), 201
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error creating beer image: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@beer_images_api_bp.route('/admin/<int:image_id>', methods=['PUT'])
@require_admin
def update_beer_image(user, image_id):
    """Update a beer image (admin only)"""
    try:
        data = request.form.to_dict()
        
        db = next(get_db())
        try:
            beer_image = db.query(BeerImage).filter(BeerImage.id == image_id).first()
            
            if not beer_image:
                return jsonify({
                    'success': False,
                    'error': 'Beer image not found'
                }), 404
            
            # Update fields
            if 'name' in data:
                beer_image.name = data['name']
            
            if 'display_order' in data:
                beer_image.display_order = int(data['display_order'])
            
            if 'is_active' in data:
                beer_image.is_active = data['is_active'].lower() == 'true'
            
            # Handle image replacement
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    if not allowed_file(file.filename):
                        return jsonify({
                            'success': False,
                            'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, WebP'
                        }), 400
                    
                    # Delete old image
                    if beer_image.image_url:
                        base_upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
                        delete_image(beer_image.image_url, base_upload_folder)
                    
                    # Upload new image
                    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'beer-images')
                    new_image_url = process_and_save_image(
                        file,
                        upload_folder,
                        max_width=800,
                        max_height=600,
                        create_responsive=False
                    )
                    
                    if not new_image_url:
                        return jsonify({
                            'success': False,
                            'error': 'Failed to process new image'
                        }), 400
                    
                    beer_image.image_url = new_image_url
            
            beer_image.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(beer_image)
            
            logger.info(f"Beer image updated: {beer_image.name} (ID: {beer_image.id})")
            
            return jsonify({
                'success': True,
                'message': 'Beer image updated successfully',
                'beer_image': beer_image.to_dict()
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error updating beer image {image_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@beer_images_api_bp.route('/admin/<int:image_id>', methods=['DELETE'])
@require_admin
def delete_beer_image(user, image_id):
    """Delete a beer image (admin only)"""
    try:
        db = next(get_db())
        try:
            beer_image = db.query(BeerImage).filter(BeerImage.id == image_id).first()
            
            if not beer_image:
                return jsonify({
                    'success': False,
                    'error': 'Beer image not found'
                }), 404
            
            # Delete image file
            if beer_image.image_url:
                base_upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
                delete_image(beer_image.image_url, base_upload_folder)
            
            image_name = beer_image.name
            db.delete(beer_image)
            db.commit()
            
            logger.info(f"Beer image deleted: {image_name} (ID: {image_id})")
            
            return jsonify({
                'success': True,
                'message': 'Beer image deleted successfully'
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error deleting beer image {image_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
