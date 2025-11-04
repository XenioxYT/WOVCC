"""Test the API login endpoint"""

import requests
import json

API_BASE = "http://localhost:5000/api"

print("=" * 60)
print("Testing API Login Endpoint")
print("=" * 60)

# Test data
test_email = "15@gmail.com"
test_password = "123456"

print(f"\nAttempting login with:")
print(f"  Email: {test_email}")
print(f"  Password: {test_password}")

try:
    response = requests.post(
        f"{API_BASE}/auth/login",
        headers={"Content-Type": "application/json"},
        json={"email": test_email, "password": test_password}
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))
    
except requests.exceptions.ConnectionError:
    print("\n✗ ERROR: Cannot connect to API server.")
    print("  Make sure the API server is running: python api.py")
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {e}")
