"""
Database migration script to add spouse card fields
Run this script to update your database schema with the new spouse card columns
"""

import sqlite3
import os
import sys

def migrate_database():
    """Add spouse card columns to database"""
    
    # Determine database path
    db_path = os.environ.get('DATABASE_URL', 'sqlite:///wovcc.db')
    if db_path.startswith('sqlite:///'):
        db_path = db_path.replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        print("Please ensure the database exists before running migration")
        sys.exit(1)
    
    print(f"📂 Database location: {db_path}")
    print("🔄 Starting migration...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        users_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(pending_registrations)")
        pending_columns = [col[1] for col in cursor.fetchall()]
        
        changes_made = False
        
        # Add has_spouse_card to users table if it doesn't exist
        if 'has_spouse_card' not in users_columns:
            print("  ✓ Adding 'has_spouse_card' column to users table...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN has_spouse_card BOOLEAN DEFAULT FALSE
            """)
            changes_made = True
        else:
            print("  ℹ 'has_spouse_card' column already exists in users table")
        
        # Add include_spouse_card to pending_registrations table if it doesn't exist
        if 'include_spouse_card' not in pending_columns:
            print("  ✓ Adding 'include_spouse_card' column to pending_registrations table...")
            cursor.execute("""
                ALTER TABLE pending_registrations 
                ADD COLUMN include_spouse_card BOOLEAN DEFAULT FALSE
            """)
            changes_made = True
        else:
            print("  ℹ 'include_spouse_card' column already exists in pending_registrations table")
        
        if changes_made:
            conn.commit()
            print("\n✅ Migration completed successfully!")
        else:
            print("\n✅ Database is already up to date - no changes needed")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM users WHERE has_spouse_card = 1")
        spouse_card_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        print(f"\n📊 Summary:")
        print(f"  Total users: {total_users}")
        print(f"  Users with spouse card: {spouse_card_count}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    print("=" * 60)
    print("  WOVCC Spouse Card Migration")
    print("=" * 60)
    print()
    
    # Confirm with user
    response = input("This will modify your database. Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Migration cancelled")
        sys.exit(0)
    
    print()
    migrate_database()
    print()
    print("=" * 60)
