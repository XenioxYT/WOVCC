"""
Script to create the first admin user
Run: python backend/create_admin.py
"""

import sys
import os

# IMPORTANT: Load environment variables FIRST before other imports
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, SessionLocal, User
from auth import hash_password


def create_admin():
    """Create admin user"""
    # Security check: Do not run in production
    if os.environ.get('FLASK_ENV') == 'production':
        print("This script is for development use only and cannot be run in production.")
        sys.exit(1)
    init_db()
    db = SessionLocal()
    
    try:
        email = input("Enter admin email (default: admin@wovcc.co.uk): ").strip() or "admin@wovcc.co.uk"
        
        # Check if admin already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User with email {email} already exists.")
            response = input("Do you want to make this user an admin? (y/n): ").strip().lower()
            if response == 'y':
                existing.is_admin = True
                existing.password_hash = hash_password(input("Enter new password: "))
                db.commit()
                print(f"User {email} is now an admin.")
            return
        
        name = input("Enter admin name (default: Admin): ").strip() or "Admin"
        password = input("Enter admin password: ").strip()
        
        if not password:
            print("Password cannot be empty!")
            return
        
        admin_user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            membership_tier='Admin',
            is_member=True,
            is_admin=True,
            newsletter=False
        )
        
        db.add(admin_user)
        db.commit()
        
        print(f"\nAdmin user created successfully!")
        print(f"Email: {email}")
        print(f"Name: {name}")
        print("\nYou can now login with these credentials.")
        
    except Exception as e:
        print(f"Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    create_admin()


