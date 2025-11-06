#!/usr/bin/env python3
"""Check the state of users and pending_registrations tables"""

from database import SessionLocal, User, PendingRegistration

db = SessionLocal()

print("=== USERS TABLE ===")
users = db.query(User).all()
for u in users:
    print(f"ID: {u.id}, Email: {u.email}, Member: {u.is_member}, Created: {u.created_at}")

print(f"\nTotal users: {len(users)}")

print("\n=== PENDING REGISTRATIONS TABLE ===")
pending = db.query(PendingRegistration).all()
for p in pending:
    print(f"ID: {p.id}, Email: {p.email}, Created: {p.created_at}")

print(f"\nTotal pending: {len(pending)}")

db.close()
