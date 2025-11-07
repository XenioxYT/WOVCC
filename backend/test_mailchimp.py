"""
Test script for Mailchimp integration
Run this to verify your Mailchimp setup is working
"""

from dotenv import load_dotenv
load_dotenv()

import os
from mailchimp import (
    is_mailchimp_configured,
    subscribe_to_newsletter,
    check_subscription_status,
    MAILCHIMP_API_KEY,
    MAILCHIMP_LIST_ID,
    MAILCHIMP_SERVER
)

def test_mailchimp_configuration():
    """Test if Mailchimp is properly configured"""
    print("=" * 60)
    print("MAILCHIMP CONFIGURATION TEST")
    print("=" * 60)
    
    print("\n1. Checking environment variables...")
    print(f"   MAILCHIMP_API_KEY: {'✓ Set' if MAILCHIMP_API_KEY else '✗ Not set'}")
    if MAILCHIMP_API_KEY:
        print(f"   Server datacenter: {MAILCHIMP_SERVER}")
    print(f"   MAILCHIMP_LIST_ID: {'✓ Set' if MAILCHIMP_LIST_ID else '✗ Not set'}")
    
    print(f"\n2. Configuration status: {'✓ Configured' if is_mailchimp_configured() else '✗ Not configured'}")
    
    if not is_mailchimp_configured():
        print("\n❌ Mailchimp is not properly configured!")
        print("   Please add MAILCHIMP_API_KEY and MAILCHIMP_LIST_ID to your .env file")
        print("\n   Get your credentials from:")
        print("   - API Key: https://mailchimp.com/ → Account → Extras → API Keys")
        print("   - List ID: https://mailchimp.com/ → Audience → Settings → Audience ID")
        return False
    
    print("\n3. Testing API connection...")
    
    # Test with a safe email that won't actually be subscribed
    test_email = "test@example.com"
    
    print(f"   Checking status of {test_email}...")
    status = check_subscription_status(test_email)
    
    if status.get('status') == 'error':
        print("   ❌ API connection failed!")
        print("   Please verify your API key is correct and active")
        return False
    
    print(f"   ✓ API connection successful!")
    print(f"   Status: {status.get('status', 'unknown')}")
    
    print("\n✅ All tests passed! Mailchimp integration is working correctly.")
    print("\nYou can now:")
    print("   1. Use the newsletter subscription forms on your website")
    print("   2. Register new users with newsletter checkbox enabled")
    print("   3. Monitor subscriptions in your Mailchimp dashboard")
    
    return True

def interactive_test():
    """Interactive test to subscribe a real email"""
    print("\n" + "=" * 60)
    print("INTERACTIVE SUBSCRIPTION TEST")
    print("=" * 60)
    
    if not is_mailchimp_configured():
        print("\n❌ Cannot run interactive test - Mailchimp not configured")
        return
    
    print("\nThis will attempt to subscribe a real email to your Mailchimp list.")
    print("WARNING: Only use test emails or your own email!")
    
    email = input("\nEnter email to test (or press Enter to skip): ").strip()
    
    if not email:
        print("Skipped interactive test.")
        return
    
    name = input("Enter name (optional): ").strip() or None
    
    print(f"\n📧 Subscribing {email}...")
    
    # First check if already subscribed
    status = check_subscription_status(email)
    if status.get('subscribed'):
        print(f"   ℹ️  Email is already subscribed (status: {status.get('status')})")
        print("   This is expected behavior - no duplicate will be created.")
    
    # Try to subscribe
    result = subscribe_to_newsletter(email, name)
    
    if result.get('success'):
        print(f"   ✅ {result.get('message')}")
        if result.get('already_subscribed'):
            print("   (No duplicate created)")
    else:
        print(f"   ❌ {result.get('message')}")
    
    print(f"\n🔍 Final subscription status:")
    final_status = check_subscription_status(email)
    print(f"   Subscribed: {final_status.get('subscribed')}")
    print(f"   Status: {final_status.get('status')}")

if __name__ == '__main__':
    try:
        # Run configuration test
        config_ok = test_mailchimp_configuration()
        
        # Offer interactive test if config is ok
        if config_ok:
            interactive_test()
            
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
