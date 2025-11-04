"""Test login functionality to debug password verification issue"""

from database import get_db, User
from auth import hash_password, verify_password

# Get database session
db = next(get_db())

print("=" * 60)
print("Testing Login Functionality")
print("=" * 60)

# Get a test user
user = db.query(User).filter(User.email == "15@gmail.com").first()

if user:
    print(f"\n✓ User found: {user.email}")
    print(f"  Name: {user.name}")
    print(f"  Password hash: {user.password_hash}")
    print(f"  Hash length: {len(user.password_hash)}")
    
    # Test various passwords
    test_passwords = ["test123", "password", "123456", "test", "15@gmail.com"]
    
    print(f"\nTesting password verification:")
    for pwd in test_passwords:
        result = verify_password(pwd, user.password_hash)
        print(f"  Password '{pwd}': {'✓ MATCH' if result else '✗ No match'}")
    
    # Create a fresh hash and test it
    print(f"\n--- Testing fresh hash creation ---")
    test_pwd = "test123"
    new_hash = hash_password(test_pwd)
    print(f"  New hash created: {new_hash}")
    verify_result = verify_password(test_pwd, new_hash)
    print(f"  Verification: {'✓ SUCCESS' if verify_result else '✗ FAILED'}")
    
else:
    print("\n✗ User not found")

# Check all users and their hash formats
print(f"\n{'=' * 60}")
print("All Users in Database:")
print(f"{'=' * 60}")
all_users = db.query(User).all()
for u in all_users:
    print(f"ID: {u.id:2d} | Email: {u.email:30s} | Hash starts: {u.password_hash[:20]}")

db.close()
