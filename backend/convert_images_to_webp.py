"""
Convert existing images to WebP format for better performance
Run this script to optimize all existing images in the assets and uploads folders
"""

from PIL import Image
import os
import sys

WEBP_QUALITY = 80

def convert_to_webp(image_path, output_path=None, quality=WEBP_QUALITY):
    """Convert an image to WebP format"""
    try:
        if output_path is None:
            output_path = os.path.splitext(image_path)[0] + '.webp'
        
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            
            # Save as WebP
            img.save(output_path, 'WebP', quality=quality, method=6)
            
            # Get file sizes
            original_size = os.path.getsize(image_path)
            webp_size = os.path.getsize(output_path)
            savings = ((original_size - webp_size) / original_size) * 100
            
            print(f"✓ {os.path.basename(image_path)}")
            print(f"  Original: {original_size / 1024:.1f} KB")
            print(f"  WebP: {webp_size / 1024:.1f} KB")
            print(f"  Savings: {savings:.1f}%\n")
            
            return True
    except Exception as e:
        print(f"✗ Error converting {image_path}: {e}\n")
        return False

def convert_directory(directory):
    """Convert all images in a directory to WebP"""
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        return
    
    print(f"\nConverting images in: {directory}\n")
    print("="*60)
    
    converted_count = 0
    skipped_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_lower = file.lower()
            if file_lower.endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(root, file)
                webp_path = os.path.splitext(image_path)[0] + '.webp'
                
                # Skip if WebP version already exists
                if os.path.exists(webp_path):
                    print(f"⊘ {file} (WebP version already exists)")
                    skipped_count += 1
                    continue
                
                if convert_to_webp(image_path, webp_path):
                    converted_count += 1
                else:
                    error_count += 1
    
    print("="*60)
    print(f"\nSummary:")
    print(f"  Converted: {converted_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")
    print()

if __name__ == '__main__':
    print("🏏 WOVCC Image Optimizer")
    print("Converting images to WebP format...\n")
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    
    # Convert assets
    assets_dir = os.path.join(base_dir, 'assets')
    convert_directory(assets_dir)
    
    # Convert uploads
    uploads_dir = os.path.join(script_dir, 'uploads')
    convert_directory(uploads_dir)
    
    print("\n✅ Image optimization complete!")
    print("\nNext steps:")
    print("1. Update HTML templates to use <picture> elements with WebP")
    print("2. Keep original files as fallbacks for older browsers")
    print("3. Test image loading in different browsers")
