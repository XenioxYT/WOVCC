"""
One-time migration script to import sponsors from CSV to database
Converts all sponsor logos to WebP format and populates the sponsors table.

Run this script once, then DELETE IT after successful migration.
"""

import os
import sys
import csv
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from database import get_db, Sponsor, init_db
from image_utils import process_and_save_image

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_sponsors():
    """Migrate sponsors from CSV to database with image conversion"""
    
    # Paths
    csv_path = os.path.join(os.path.dirname(__file__), 'sponsors.csv')
    old_assets_folder = os.path.join(os.path.dirname(__file__), '..', 'assets', 'sponsors')
    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'sponsors')
    
    # Ensure database is initialized
    logger.info("Initializing database...")
    init_db()
    
    # Create uploads/sponsors folder
    os.makedirs(upload_folder, exist_ok=True)
    logger.info(f"Created/verified upload folder: {upload_folder}")
    
    # Check if CSV exists
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        return False
    
    # Check if old assets folder exists
    if not os.path.exists(old_assets_folder):
        logger.error(f"Assets folder not found: {old_assets_folder}")
        return False
    
    # Read CSV
    logger.info(f"Reading sponsors from {csv_path}...")
    sponsors_data = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            sponsors_data = list(reader)
        
        logger.info(f"Found {len(sponsors_data)} sponsors in CSV")
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        return False
    
    # Process each sponsor
    db = next(get_db())
    try:
        migrated_count = 0
        failed_count = 0
        
        for idx, sponsor_row in enumerate(sponsors_data):
            name = sponsor_row.get('name', '').strip()
            old_filename = sponsor_row.get('file_name', '').strip()
            website_url = sponsor_row.get('url', '').strip()
            
            if not name or not old_filename:
                logger.warning(f"Skipping row {idx+1}: Missing name or filename")
                failed_count += 1
                continue
            
            logger.info(f"\n[{idx+1}/{len(sponsors_data)}] Processing: {name}")
            
            # Check if sponsor already exists
            existing = db.query(Sponsor).filter(Sponsor.name == name).first()
            if existing:
                logger.info(f"  ✓ Sponsor '{name}' already exists in database (ID: {existing.id}). Skipping.")
                migrated_count += 1
                continue
            
            # Find and process old logo
            old_logo_path = os.path.join(old_assets_folder, old_filename)
            
            if not os.path.exists(old_logo_path):
                logger.warning(f"  ✗ Logo file not found: {old_logo_path}")
                failed_count += 1
                continue
            
            try:
                # Open image file and process it
                logger.info(f"  → Converting {old_filename} to WebP...")
                
                with open(old_logo_path, 'rb') as img_file:
                    # Create a file-like object that process_and_save_image can use
                    from io import BytesIO
                    from werkzeug.datastructures import FileStorage
                    
                    # Read the image into memory
                    img_bytes = BytesIO(img_file.read())
                    img_bytes.seek(0)
                    
                    # Create FileStorage object
                    file_storage = FileStorage(
                        stream=img_bytes,
                        filename=old_filename,
                        content_type='image/png'
                    )
                    
                    # Process and save image
                    logo_url = process_and_save_image(
                        file_storage,
                        upload_folder,
                        max_height=80,
                        create_responsive=False,
                        height_only=True
                    )
                    
                    if not logo_url:
                        logger.warning(f"  ✗ Failed to process image: {old_filename}")
                        failed_count += 1
                        continue
                    
                    logger.info(f"  ✓ Converted to: {logo_url}")
                
                # Create database entry
                new_sponsor = Sponsor(
                    name=name,
                    logo_url=logo_url,
                    website_url=website_url if website_url else None,
                    display_order=idx,  # Use CSV order
                    is_active=True
                )
                
                db.add(new_sponsor)
                db.commit()
                db.refresh(new_sponsor)
                
                logger.info(f"  ✓ Created database entry (ID: {new_sponsor.id})")
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"  ✗ Error processing {name}: {e}")
                db.rollback()
                failed_count += 1
                continue
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total sponsors in CSV: {len(sponsors_data)}")
        logger.info(f"Successfully migrated: {migrated_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info("="*60)
        
        if migrated_count > 0:
            logger.info("\n✅ Migration completed successfully!")
            logger.info("\nNext steps:")
            logger.info("1. Verify sponsors display correctly on the website")
            logger.info("2. Check admin panel for sponsor management")
            logger.info("3. DELETE this migration script (migrate_sponsors.py)")
            logger.info("4. Optionally backup and remove old sponsor images from assets/sponsors/")
            return True
        else:
            logger.warning("\n⚠️  No sponsors were migrated!")
            return False
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == '__main__':
    logger.info("="*60)
    logger.info("WOVCC Sponsor Migration Script")
    logger.info("="*60)
    logger.info("This script will:")
    logger.info("1. Read sponsors from sponsors.csv")
    logger.info("2. Convert logos to WebP format (max height 80px)")
    logger.info("3. Save to uploads/sponsors/ folder")
    logger.info("4. Create database entries")
    logger.info("="*60)
    
    input("\nPress ENTER to start migration or Ctrl+C to cancel...")
    
    success = migrate_sponsors()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
