#!/usr/bin/env python
"""
Test script for Stripe checkout endpoint
"""
import os
import sys
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test the stripe_config module directly
from stripe_config import create_checkout_session, STRIPE_SECRET_KEY, MEMBERSHIP_PRODUCT_ID, MEMBERSHIP_PRICE_ID

print("="*60)
print("Stripe Configuration Test")
print("="*60)
print(f"STRIPE_SECRET_KEY: {'SET' if STRIPE_SECRET_KEY else 'NOT SET'}")
print(f"MEMBERSHIP_PRODUCT_ID: {MEMBERSHIP_PRODUCT_ID}")
print(f"MEMBERSHIP_PRICE_ID: {MEMBERSHIP_PRICE_ID if MEMBERSHIP_PRICE_ID else 'NOT SET'}")
print("="*60)

if not STRIPE_SECRET_KEY:
    print("ERROR: STRIPE_SECRET_KEY not set!")
    sys.exit(1)

print("\nTesting create_checkout_session...")
try:
    session = create_checkout_session(
        email="test@example.com",
        user_id=999
    )
    print(f"✓ SUCCESS! Session ID: {session.id}")
    print(f"  Checkout URL: {session.url}")
    print(f"  Status: {session.status}")
except Exception as e:
    print(f"✗ FAILED: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("All tests passed!")
print("="*60)
