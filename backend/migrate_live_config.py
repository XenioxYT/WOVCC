#!/usr/bin/env python3
"""
Migrate live_config.json to PostgreSQL database

This script migrates the existing live_config.json file to the new
LiveConfig database table. Run this once after deploying the database migration.

Usage:
    python migrate_live_config.py
"""

import os
import sys
import json
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from database import get_db, LiveConfig

def migrate_live_config():
    """Migrate live_config.json to database"""
    config_file = os.path.join(os.path.dirname(__file__), 'live_config.json')
    
    # Check if JSON file exists
    if not os.path.exists(config_file):
        print("No live_config.json found. Nothing to migrate.")
        return True
    
    # Load existing config
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Loaded config from {config_file}")
        print(f"  is_live: {config.get('is_live', False)}")
        print(f"  livestream_url: {config.get('livestream_url', '')}")
        print(f"  selected_match: {config.get('selected_match')}")
        print(f"  last_updated: {config.get('last_updated')}")
    except json.JSONDecodeError as e:
        print(f"Error reading live_config.json: {e}")
        return False
    
    # Get database session
    db = next(get_db())
    try:
        # Check if config already exists in database
        existing = db.query(LiveConfig).filter(LiveConfig.id == 1).first()
        
        if existing:
            print("\nLive config already exists in database. Updating...")
            existing.is_live = config.get('is_live', False)
            existing.livestream_url = config.get('livestream_url', '')
            if config.get('selected_match'):
                existing.selected_match_data = json.dumps(config['selected_match'])
            else:
                existing.selected_match_data = None
            existing.last_updated = datetime.now()
        else:
            print("\nCreating new live config in database...")
            new_config = LiveConfig(
                id=1,
                is_live=config.get('is_live', False),
                livestream_url=config.get('livestream_url', ''),
                selected_match_data=json.dumps(config['selected_match']) if config.get('selected_match') else None,
                last_updated=datetime.now()
            )
            db.add(new_config)
        
        db.commit()
        print("✅ Successfully migrated live_config to database!")
        
        # Optionally backup and remove the old JSON file
        backup_file = config_file + '.backup'
        os.rename(config_file, backup_file)
        print(f"📁 Original file backed up to: {backup_file}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error migrating live_config: {e}")
        return False
    finally:
        db.close()


if __name__ == '__main__':
    success = migrate_live_config()
    sys.exit(0 if success else 1)
