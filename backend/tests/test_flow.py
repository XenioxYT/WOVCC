"""
End-to-end test for Stripe checkout flow
Tests: Register -> Create Checkout -> (Simulated Webhook) -> Verify Membership
"""
import requests
import json
import time

API_BASE = "http://127.0.0.1:5000/api"

print("="*70)
print("STRIPE CHECKOUT FLOW - END-TO-END TEST")
print("="*70)

# Step 1: Register a new user
print("\n[1] Registering new user...")
email = f"testuser{int(time.time())}@test.com"
password = "testpass123"
name = "Test User"

register_response = requests.post(f"{API_BASE}/auth/pre-register", json={
    "email": email,
    "password": password,
    "name": name,
    "newsletter": True
})

if register_response.status_code != 201:
    print(f"✗ Registration failed: {register_response.status_code}")
    print(register_response.text)
    exit(1)

register_data = register_response.json()
access_token = register_data.get("access_token")
user_id = register_data.get("user", {}).get("id")

print(f"✓ User registered successfully")
print(f"  Email: {email}")
print(f"  User ID: {user_id}")
print(f"  Is Member: {register_data.get('user', {}).get('is_member')}")

# Step 2: Create Stripe Checkout Session
print("\n[2] Creating Stripe Checkout session...")
checkout_response = requests.post(
    f"{API_BASE}/payments/create-checkout",
    headers={"Authorization": f"Bearer {access_token}"}
)

if checkout_response.status_code != 200:
    print(f"✗ Checkout creation failed: {checkout_response.status_code}")
    print(checkout_response.text)
    exit(1)

checkout_data = checkout_response.json()
checkout_url = checkout_data.get("checkout_url")
session_id = checkout_data.get("session_id")

print(f"✓ Checkout session created")
print(f"  Session ID: {session_id}")
print(f"  Checkout URL: {checkout_url[:80]}...")

# Step 3: Simulate Stripe webhook (checkout.session.completed)
print("\n[3] Simulating Stripe webhook (checkout.session.completed)...")
webhook_payload = {
    "id": "evt_test_webhook",
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": session_id,
            "payment_status": "paid",
            "customer_email": email,
            "metadata": {
                "user_id": str(user_id)
            }
        }
    }
}

webhook_response = requests.post(
    f"{API_BASE}/payments/webhook",
    json=webhook_payload,
    headers={"Content-Type": "application/json"}
)

if webhook_response.status_code not in [200, 400]:
    print(f"⚠ Webhook returned status: {webhook_response.status_code}")
    print(webhook_response.text)
else:
    print(f"✓ Webhook processed (status: {webhook_response.status_code})")

# Step 4: Verify user profile is updated
print("\n[4] Verifying user membership status...")
time.sleep(1)  # Brief pause to ensure database is updated

profile_response = requests.get(
    f"{API_BASE}/user/profile",
    headers={"Authorization": f"Bearer {access_token}"}
)

if profile_response.status_code != 200:
    print(f"✗ Failed to fetch profile: {profile_response.status_code}")
    print(profile_response.text)
    exit(1)

profile_data = profile_response.json()
user = profile_data.get("user", {})
is_member = user.get("is_member")
payment_status = user.get("payment_status")

print(f"  Is Member: {is_member}")
print(f"  Payment Status: {payment_status}")

if is_member and payment_status == "active":
    print("\n" + "="*70)
    print("✓ SUCCESS! Full checkout flow completed successfully!")
    print("="*70)
else:
    print("\n" + "="*70)
    print(f"✗ FAILED! Membership not activated correctly")
    print(f"  Expected: is_member=True, payment_status='active'")
    print(f"  Got: is_member={is_member}, payment_status={payment_status}")
    print("="*70)
    exit(1)
