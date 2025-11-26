#!/usr/bin/env python3
"""
Migrate scraped_data.json to PostgreSQL database

This script migrates the existing scraped_data.json file to the new
ScrapedData database table. Run this once after deploying the database migration.

Usage:
    python migrate_scraped_data.py
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

from database import get_db, ScrapedData

def migrate_scraped_data():
    """Migrate scraped_data.json to database"""
    json_file = os.path.join(os.path.dirname(__file__), 'scraped_data.json')
    
    # Check if JSON file exists
    if not os.path.exists(json_file):
        print("No scraped_data.json found. Nothing to migrate.")
        print("The scraper daemon will populate the database on first run.")
        return True
    
    # Load existing data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded data from {json_file}")
        print(f"  Teams: {len(data.get('teams', []))}")
        print(f"  Fixtures: {len(data.get('fixtures', []))}")
        print(f"  Results: {len(data.get('results', []))}")
        print(f"  Last updated: {data.get('last_updated')}")
    except json.JSONDecodeError as e:
        print(f"Error reading scraped_data.json: {e}")
        return False
    
    # Get database session
    db = next(get_db())
    try:
        # Check if data already exists in database
        existing = db.query(ScrapedData).filter(ScrapedData.id == 1).first()
        
        if existing and existing.teams_data:
            print("\nScraped data already exists in database.")
            response = input("Overwrite with JSON file data? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return True
        
        # Use the update_from_scrape method
        ScrapedData.update_from_scrape(
            db,
            teams=data.get('teams', []),
            fixtures=data.get('fixtures', []),
            results=data.get('results', []),
            success=True,
            error_message=None
        )
        
        print("\n✅ Successfully migrated scraped_data to database!")
        
        # Optionally backup the old JSON file
        backup_file = json_file + '.backup'
        if not os.path.exists(backup_file):
            import shutil
            shutil.copy2(json_file, backup_file)
            print(f"📁 Original file backed up to: {backup_file}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error migrating scraped_data: {e}")
        return False
    finally:
        db.close()


if __name__ == '__main__':
    success = migrate_scraped_data()
    sys.exit(0 if success else 1)
