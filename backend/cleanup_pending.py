#!/usr/bin/env python3
"""
Clean up the pending_registrations table
Remove any pending registrations where the user already exists in the users table
"""

from database import SessionLocal, User, PendingRegistration

db = SessionLocal()

print("=== CLEANING UP PENDING REGISTRATIONS ===\n")

# Get all pending registrations
pending_list = db.query(PendingRegistration).all()
print(f"Found {len(pending_list)} pending registrations")

# Check each one
to_delete = []
for pending in pending_list:
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == pending.email).first()
    if existing_user:
        print(f"  ❌ {pending.email} (ID: {pending.id}) - Already exists in users table (User ID: {existing_user.id})")
        to_delete.append(pending)
    else:
        print(f"  ✓ {pending.email} (ID: {pending.id}) - No user account found, keeping pending")

print(f"\n=== SUMMARY ===")
print(f"Total pending registrations: {len(pending_list)}")
print(f"To delete (already have accounts): {len(to_delete)}")
print(f"To keep (waiting for payment): {len(pending_list) - len(to_delete)}")

if to_delete:
    confirm = input(f"\nDelete {len(to_delete)} completed pending registrations? (yes/no): ")
    if confirm.lower() == 'yes':
        for pending in to_delete:
            db.delete(pending)
        db.commit()
        print(f"✓ Deleted {len(to_delete)} pending registrations")
    else:
        print("Cancelled, no changes made")
else:
    print("\nNo cleanup needed!")

db.close()
