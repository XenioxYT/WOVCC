"""
Database Migration: Add slugs to existing events

This script:
1. Adds the 'slug' column to the events table if it doesn't exist
2. Generates SEO-friendly URL slugs for all events that don't have one

Run this inside the Docker container:
    docker compose exec web python backend/migrate_event_slugs.py

Usage:
    python migrate_event_slugs.py         # Run full migration
    python migrate_event_slugs.py --show  # Show current slugs only
"""

import os
import sys

# Add the backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import get_db, Event, engine, init_db
from slug_utils import generate_event_slug
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def add_slug_column_if_not_exists():
    """Add the slug column to the events table if it doesn't exist."""
    logger.info("Checking if 'slug' column exists in events table...")
    
    with engine.connect() as conn:
        # Check if column exists (PostgreSQL specific)
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'events' AND column_name = 'slug'
        """))
        
        if result.fetchone() is None:
            logger.info("Adding 'slug' column to events table...")
            conn.execute(text("""
                ALTER TABLE events 
                ADD COLUMN slug VARCHAR(300) UNIQUE
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_events_slug ON events (slug)
            """))
            conn.commit()
            logger.info("✅ 'slug' column added successfully!")
            return True
        else:
            logger.info("✅ 'slug' column already exists.")
            return False


def migrate_event_slugs():
    """Add slugs to all events that don't have one."""
    # First ensure the column exists
    add_slug_column_if_not_exists()
    
    db = next(get_db())
    try:
        # Find all events without slugs
        events_without_slugs = db.query(Event).filter(
            (Event.slug.is_(None)) | (Event.slug == '')
        ).all()
        
        if not events_without_slugs:
            logger.info("✅ All events already have slugs. Nothing to migrate.")
            return
        
        logger.info(f"Found {len(events_without_slugs)} events without slugs. Migrating...")
        
        migrated_count = 0
        for event in events_without_slugs:
            try:
                # Generate a unique slug for this event
                new_slug = generate_event_slug(event.title, event.date, db, exclude_id=event.id)
                
                if new_slug:
                    event.slug = new_slug
                    migrated_count += 1
                    logger.info(f"  → Event {event.id}: '{event.title[:40]}' → /events/{new_slug}")
                else:
                    logger.warning(f"  ⚠ Event {event.id}: Could not generate slug for '{event.title}'")
                    
            except Exception as e:
                logger.error(f"  ✗ Event {event.id}: Error generating slug - {e}")
        
        # Commit all changes
        db.commit()
        logger.info(f"\n✅ Migration complete! Added slugs to {migrated_count}/{len(events_without_slugs)} events.")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def show_current_slugs():
    """Display all current event slugs."""
    # Ensure column exists first
    add_slug_column_if_not_exists()
    
    db = next(get_db())
    try:
        events = db.query(Event).order_by(Event.date.desc()).all()
        
        if not events:
            logger.info("No events found in database.")
            return
        
        print("\n📋 Current Event URLs:")
        print("-" * 80)
        
        for event in events:
            slug_status = f"/events/{event.slug}" if event.slug else f"[ID only: /events/{event.id}]"
            published = "✓" if event.is_published else "✗"
            title_truncated = event.title[:35] + "..." if len(event.title) > 35 else event.title
            print(f"  {published} {title_truncated:<40} → {slug_status}")
        
        print("-" * 80)
        
        # Count stats
        with_slugs = sum(1 for e in events if e.slug)
        without_slugs = len(events) - with_slugs
        print(f"\nTotal: {len(events)} events | With slugs: {with_slugs} | Without slugs: {without_slugs}")
        
    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate event slugs for SEO-friendly URLs')
    parser.add_argument('--show', action='store_true', help='Show current slugs without migrating')
    args = parser.parse_args()
    
    print("=" * 60)
    print("WOVCC Event Slug Migration")
    print("=" * 60)
    
    if args.show:
        show_current_slugs()
    else:
        migrate_event_slugs()
        print("\n")
        show_current_slugs()
