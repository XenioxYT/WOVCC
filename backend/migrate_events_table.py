"""
Migration script to add missing columns to events table
Run this once to update existing database
"""

import sqlite3
import os

def migrate_events_table():
    """Add interested_count column to existing events table and fix event_interests"""
    db_path = 'wovcc.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if interested_count column exists in events
        cursor.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'interested_count' not in columns:
            print("Adding interested_count column to events table...")
            cursor.execute("ALTER TABLE events ADD COLUMN interested_count INTEGER DEFAULT 0")
            conn.commit()
            print("✓ Successfully added interested_count column")
        else:
            print("✓ interested_count column already exists")
        
        # Check event_interests table columns
        cursor.execute("PRAGMA table_info(event_interests)")
        interest_columns = [column[1] for column in cursor.fetchall()]
        
        if not interest_columns:
            # Table doesn't exist, create it
            print("Creating event_interests table...")
            cursor.execute("""
                CREATE TABLE event_interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    user_id INTEGER,
                    user_email VARCHAR(255),
                    user_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("✓ event_interests table created")
        else:
            # Table exists, check for missing columns
            print("Checking event_interests table columns...")
            
            if 'user_email' not in interest_columns:
                print("Adding user_email column to event_interests...")
                cursor.execute("ALTER TABLE event_interests ADD COLUMN user_email VARCHAR(255)")
                conn.commit()
                print("✓ Added user_email column")
            else:
                print("✓ user_email column already exists")
            
            if 'user_name' not in interest_columns:
                print("Adding user_name column to event_interests...")
                cursor.execute("ALTER TABLE event_interests ADD COLUMN user_name VARCHAR(255)")
                conn.commit()
                print("✓ Added user_name column")
            else:
                print("✓ user_name column already exists")
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_interests_event_id ON event_interests(event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_interests_user_id ON event_interests(user_id)")
        conn.commit()
        print("✓ Indexes created")
        
        print("\n✅ Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"❌ Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_events_table()
