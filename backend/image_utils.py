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


def process_and_save_image(file, upload_folder, max_width=MAX_WIDTH, max_height=MAX_HEIGHT):
    """
    Process and save an uploaded image - always converts to WebP only
    
    Args:
        file: FileStorage object from Flask request
        upload_folder: Directory to save the processed image
        max_width: Maximum width (default: 1920px)
        max_height: Maximum height (default: 1080px)
    
    Returns:
        str: Relative path to saved WebP image or None if error
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
        
        # Generate base filename (without extension)
        original_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d')
        base_filename = f"{timestamp}_{unique_id}"
        
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
        
        # Save only WebP version with high compression
        webp_filename = f"{base_filename}.webp"
        webp_filepath = os.path.join(upload_folder, webp_filename)
        img.save(webp_filepath, 'WebP', quality=WEBP_QUALITY, method=6)
        
        logger.info(f"Image processed and saved as WebP: {webp_filename}")
        return f"/uploads/events/{webp_filename}"
        
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        return None


def delete_image(image_path, base_upload_folder):
    """
    Delete an image file
    
    Args:
        image_path: Relative path to image (e.g., /uploads/events/image.jpg)
        base_upload_folder: Base upload directory (e.g., backend/uploads)
    
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        if not image_path:
            return False
        
        # Convert relative path to absolute
        # Remove leading slash and "uploads/" prefix
        filename = image_path.replace('/uploads/events/', '')
        full_path = os.path.join(base_upload_folder, 'events', filename)
        
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error deleting image: {e}")
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
