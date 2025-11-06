"""
Convert all PNG/JPG images to WebP format and delete originals
This includes assets (banners, logos) and event uploads
"""

import os
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

WEBP_QUALITY = 80

def convert_to_webp(input_path, output_path, delete_original=True):
    """
    Convert a single image to WebP format
    
    Args:
        input_path: Path to original image
        output_path: Path for WebP output
        delete_original: Whether to delete the original file after conversion
    
    Returns:
        tuple: (success, original_size, webp_size, saved_bytes, saved_percent)
    """
    try:
        # Get original file size
        original_size = os.path.getsize(input_path)
        
        # Open and convert image
        with Image.open(input_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Save as WebP
            img.save(output_path, 'WebP', quality=WEBP_QUALITY, method=6)
        
        # Get WebP file size
        webp_size = os.path.getsize(output_path)
        saved_bytes = original_size - webp_size
        saved_percent = (saved_bytes / original_size * 100) if original_size > 0 else 0
        
        logger.info(f"✓ {os.path.basename(input_path)}")
        logger.info(f"  Original: {original_size:,} bytes → WebP: {webp_size:,} bytes")
        logger.info(f"  Saved: {saved_bytes:,} bytes ({saved_percent:.1f}%)")
        
        # Delete original if requested
        if delete_original:
            os.remove(input_path)
            logger.info(f"  Deleted original: {input_path}")
        
        return True, original_size, webp_size, saved_bytes, saved_percent
        
    except (IOError, Image.UnidentifiedImageError) as e:
        logger.error(f"✗ Failed to convert {input_path}: {e}")
        return False, 0, 0, 0, 0


def convert_directory(directory, delete_originals=True):
    """
    Convert all PNG/JPG images in a directory to WebP
    
    Args:
        directory: Directory to scan for images
        delete_originals: Whether to delete original files after conversion
    
    Returns:
        dict: Statistics about the conversion
    """
    stats = {
        'total_files': 0,
        'converted': 0,
        'failed': 0,
        'skipped': 0,
        'original_size': 0,
        'webp_size': 0,
        'saved_bytes': 0
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Scanning directory: {directory}")
    logger.info(f"{'='*60}\n")
    
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return stats
    
    # Walk through directory
    for root, dirs, files in os.walk(directory):
        for filename in files:
            # Check if it's a PNG or JPG
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
            
            stats['total_files'] += 1
            input_path = os.path.join(root, filename)
            
            # Create WebP filename
            base_name = os.path.splitext(filename)[0]
            webp_filename = f"{base_name}.webp"
            output_path = os.path.join(root, webp_filename)
            
            # Skip if WebP already exists
            if os.path.exists(output_path):
                logger.info(f"⊘ Skipped {filename} (WebP already exists)")
                stats['skipped'] += 1
                continue
            
            # Convert
            success, orig_size, webp_size, saved, percent = convert_to_webp(
                input_path, output_path, delete_original=delete_originals
            )
            
            if success:
                stats['converted'] += 1
                stats['original_size'] += orig_size
                stats['webp_size'] += webp_size
                stats['saved_bytes'] += saved
            else:
                stats['failed'] += 1
            
            print()  # Blank line between files
    
    return stats


def print_summary(all_stats):
    """Print summary of all conversions"""
    total_original = sum(s['original_size'] for s in all_stats.values())
    total_webp = sum(s['webp_size'] for s in all_stats.values())
    total_saved = sum(s['saved_bytes'] for s in all_stats.values())
    total_converted = sum(s['converted'] for s in all_stats.values())
    total_failed = sum(s['failed'] for s in all_stats.values())
    total_skipped = sum(s['skipped'] for s in all_stats.values())
    
    logger.info(f"\n{'='*60}")
    logger.info("CONVERSION SUMMARY")
    logger.info(f"{'='*60}\n")
    
    for dir_name, stats in all_stats.items():
        if stats['total_files'] > 0:
            logger.info(f"{dir_name}:")
            logger.info(f"  Files found: {stats['total_files']}")
            logger.info(f"  Converted: {stats['converted']}")
            logger.info(f"  Failed: {stats['failed']}")
            logger.info(f"  Skipped: {stats['skipped']}")
            if stats['converted'] > 0:
                saved_percent = (stats['saved_bytes'] / stats['original_size'] * 100) if stats['original_size'] > 0 else 0
                logger.info(f"  Space saved: {stats['saved_bytes']:,} bytes ({saved_percent:.1f}%)")
            logger.info("")
    
    logger.info(f"TOTAL:")
    logger.info(f"  Files converted: {total_converted}")
    logger.info(f"  Files failed: {total_failed}")
    logger.info(f"  Files skipped: {total_skipped}")
    
    if total_converted > 0:
        total_saved_percent = (total_saved / total_original * 100) if total_original > 0 else 0
        logger.info(f"  Original size: {total_original:,} bytes ({total_original / (1024*1024):.2f} MB)")
        logger.info(f"  WebP size: {total_webp:,} bytes ({total_webp / (1024*1024):.2f} MB)")
        logger.info(f"  Total saved: {total_saved:,} bytes ({total_saved / (1024*1024):.2f} MB)")
        logger.info(f"  Reduction: {total_saved_percent:.1f}%")
    
    logger.info(f"\n{'='*60}\n")


def main():
    """Main conversion script"""
    # Get the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    
    # Define directories to convert
    directories = {
        'Assets (images)': os.path.join(project_root, 'assets', 'images'),
        'Event uploads': os.path.join(backend_dir, 'uploads', 'events'),
    }
    
    # Ask for confirmation
    logger.info("\n" + "="*60)
    logger.info("IMAGE CONVERSION TO WEBP")
    logger.info("="*60)
    logger.info("\nThis script will:")
    logger.info("  1. Convert all PNG/JPG images to WebP format")
    logger.info("  2. Delete the original PNG/JPG files")
    logger.info("  3. Preserve WebP files that already exist")
    logger.info("\nDirectories to process:")
    for name, path in directories.items():
        exists = "✓" if os.path.exists(path) else "✗"
        logger.info(f"  {exists} {name}: {path}")
    
    response = input("\n⚠️  Continue with conversion and deletion? (yes/no): ")
    if response.lower() != 'yes':
        logger.info("Conversion cancelled.")
        return
    
    # Convert all directories
    all_stats = {}
    for name, directory in directories.items():
        all_stats[name] = convert_directory(directory, delete_originals=True)
    
    # Print summary
    print_summary(all_stats)


if __name__ == '__main__':
    main()
