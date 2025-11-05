"""
Image processing utilities for WOVCC
Handles image upload, resizing, and optimization
"""

from PIL import Image
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Image settings
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_WIDTH = 1920  # Max width for images
MAX_HEIGHT = 1080  # Max height for images
QUALITY = 85  # JPEG/WebP quality


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
    Process and save an uploaded image
    
    Args:
        file: FileStorage object from Flask request
        upload_folder: Directory to save the processed image
        max_width: Maximum width (default: 1920px)
        max_height: Maximum height (default: 1080px)
    
    Returns:
        str: Relative path to saved image or None if error
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
        
        # Generate unique filename
        filename = generate_unique_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        
        # Open and process image
        img = Image.open(file)
        
        # Convert RGBA to RGB if necessary (for JPEG)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Get original dimensions
        original_width, original_height = img.size
        
        # Calculate aspect ratio
        aspect_ratio = original_width / original_height
        
        # Determine new dimensions while maintaining aspect ratio
        if original_width > max_width or original_height > max_height:
            if aspect_ratio > 1:  # Landscape
                new_width = min(max_width, original_width)
                new_height = int(new_width / aspect_ratio)
            else:  # Portrait or square
                new_height = min(max_height, original_height)
                new_width = int(new_height * aspect_ratio)
            
            # Resize image with high-quality resampling
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save optimized image
        if filename.lower().endswith('.png'):
            img.save(filepath, 'PNG', optimize=True)
        elif filename.lower().endswith('.webp'):
            img.save(filepath, 'WebP', quality=QUALITY)
        else:
            img.save(filepath, 'JPEG', quality=QUALITY, optimize=True)
        
        # Return relative path (for storing in database)
        relative_path = f"/uploads/events/{filename}"
        return relative_path
        
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
