"""
Image processing utilities for WOVCC
Handles image upload, resizing, and optimization
"""

from PIL import Image
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Image settings
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_WIDTH = 1920  # Max width for images
MAX_HEIGHT = 1080  # Max height for images
QUALITY = 85  # JPEG/WebP quality
WEBP_QUALITY = 80  # WebP quality (slightly lower for better compression)

# Responsive image sizes
RESPONSIVE_SIZES = [
    {'suffix': '_thumb', 'width': 400, 'height': 300},
    {'suffix': '_medium', 'width': 800, 'height': 600},
    {'suffix': '_large', 'width': 1200, 'height': 900},
]


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving extension"""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime('%Y%m%d')
    return f"{timestamp}_{unique_id}.{ext}"


def process_and_save_image(file, upload_folder, max_width=MAX_WIDTH, max_height=MAX_HEIGHT, create_webp=True, create_responsive=True):
    """
    Process and save an uploaded image as WebP only
    
    Args:
        file: FileStorage object from Flask request
        upload_folder: Directory to save the processed image
        max_width: Maximum width (default: 1920px)
        max_height: Maximum height (default: 1080px)
        create_webp: Always True - only WebP format used
        create_responsive: Create responsive image sizes (default: True)
    
    Returns:
        str: Relative path to WebP image or None if error
    """
    try:
        # Validate file
        if not file or file.filename == '':
            return None
        
        if not allowed_file(file.filename):
            raise ValueError('Invalid file type. Allowed: PNG, JPG, JPEG, WebP')
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f'File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024)}MB')
        
        # Create upload folder if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate base filename (always .webp)
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d')
        base_filename = f"{timestamp}_{unique_id}.webp"
        
        # Open and process image
        img = Image.open(file)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Get original dimensions
        original_width, original_height = img.size
        aspect_ratio = original_width / original_height
        
        # Resize if too large
        if original_width > max_width or original_height > max_height:
            if aspect_ratio > 1:  # Landscape
                new_width = min(max_width, original_width)
                new_height = int(new_width / aspect_ratio)
            else:  # Portrait or square
                new_height = min(max_height, original_height)
                new_width = int(new_height * aspect_ratio)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save main WebP version
        webp_filepath = os.path.join(upload_folder, base_filename)
        img.save(webp_filepath, 'WebP', quality=WEBP_QUALITY, method=6)
        result_path = f"/uploads/events/{base_filename}"
        
        # Create responsive versions in WebP
        if create_responsive:
            for size_config in RESPONSIVE_SIZES:
                suffix = size_config['suffix']
                target_width = size_config['width']
                target_height = size_config['height']
                
                # Only create if original is larger
                if img.width > target_width or img.height > target_height:
                    # Calculate new dimensions maintaining aspect ratio
                    if aspect_ratio > 1:
                        new_w = min(target_width, img.width)
                        new_h = int(new_w / aspect_ratio)
                    else:
                        new_h = min(target_height, img.height)
                        new_w = int(new_h * aspect_ratio)
                    
                    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    
                    # Save WebP version
                    responsive_filename = f"{timestamp}_{unique_id}{suffix}.webp"
                    responsive_filepath = os.path.join(upload_folder, responsive_filename)
                    resized.save(responsive_filepath, 'WebP', quality=WEBP_QUALITY, method=6)
        
        logger.info(f"Image processed successfully as WebP: {base_filename}")
        return result_path
        
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        return None


def delete_image(image_path, base_upload_folder):
    """
    Delete an image file and all its responsive versions
    
    Args:
        image_path: Relative path to image (e.g., /uploads/events/image.webp)
        base_upload_folder: Base upload directory (e.g., backend/uploads)
    
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        if not image_path:
            return False
        
        # Security: Validate the image path to prevent path traversal attacks
        # Only allow paths starting with /uploads/events/
        if not image_path.startswith('/uploads/events/'):
            logger.error(f"Security: Invalid image path attempted: {image_path}")
            return False
        
        # Extract just the filename (everything after /uploads/events/)
        filename = image_path[len('/uploads/events/'):]
        
        # Security: Ensure filename doesn't contain path traversal sequences
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.error(f"Security: Path traversal attempt detected: {filename}")
            return False
        
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            logger.error(f"Security: Unsafe filename rejected: {filename}")
            return False
        
        # Construct the absolute path securely
        events_folder = os.path.join(base_upload_folder, 'events')
        full_path = os.path.join(events_folder, safe_filename)
        
        # Security: Verify the resolved path is still within the allowed directory
        # This prevents symlink attacks
        events_folder_abs = os.path.abspath(events_folder)
        full_path_abs = os.path.abspath(full_path)
        
        if not full_path_abs.startswith(events_folder_abs + os.sep):
            logger.error(f"Security: Path traversal blocked: {full_path_abs}")
            return False
        
        deleted = False
        
        # Delete main image
        if os.path.exists(full_path_abs):
            os.remove(full_path_abs)
            logger.info(f"Deleted main image: {safe_filename}")
            deleted = True
        
        # Delete responsive versions if they exist
        base_name = os.path.splitext(safe_filename)[0]
        for size_config in RESPONSIVE_SIZES:
            suffix = size_config['suffix']
            responsive_filename = f"{base_name}{suffix}.webp"
            responsive_path = os.path.join(events_folder, responsive_filename)
            responsive_path_abs = os.path.abspath(responsive_path)
            
            # Security: Verify each responsive image path as well
            if not responsive_path_abs.startswith(events_folder_abs + os.sep):
                logger.error(f"Security: Path traversal blocked for responsive image: {responsive_path_abs}")
                continue
            
            if os.path.exists(responsive_path_abs):
                os.remove(responsive_path_abs)
                logger.info(f"Deleted responsive image: {responsive_filename}")
                deleted = True
        
        return deleted
        
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        return False


def get_image_dimensions(image_path):
    """
    Get dimensions of an image
    
    Args:
        image_path: Full path to image file
    
    Returns:
        tuple: (width, height) or None if error
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return None
