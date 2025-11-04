"""
WOVCC Stripe Configuration
Handles Stripe payment integration
"""

import stripe
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')  # Use test key: sk_test_...
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')  # Use test key: pk_test_...
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')  # For webhook verification
MEMBERSHIP_PRICE_ID = os.environ.get('STRIPE_PRICE_ID', '')  # Optional: Price ID for £15 membership (price_...)
# Optional product id (prod_...); default to the product ID you provided
MEMBERSHIP_PRODUCT_ID = os.environ.get('STRIPE_PRODUCT_ID')
MEMBERSHIP_AMOUNT = 1500  # £15.00 in pence

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    print("WARNING: STRIPE_SECRET_KEY not set. Stripe functionality will be disabled.")


def create_checkout_session(customer_id: str = None, email: str = None, user_id: int = None):
    """
    Create a Stripe Checkout session for membership payment
    
    Args:
        customer_id: Existing Stripe customer ID (for renewals)
        email: Customer email (for new customers)
        user_id: User ID to include in metadata
    
    Returns:
        Stripe Checkout Session object
    """
    if not STRIPE_SECRET_KEY:
        raise ValueError("Stripe is not configured. Please set STRIPE_SECRET_KEY environment variable.")
    
    # Ensure Stripe API key is set
    if not stripe.api_key:
        stripe.api_key = STRIPE_SECRET_KEY
    
    # Determine the base URL for frontend redirects
    # In development, frontend is served from file:// or a different port
    # In production, use the environment variable or default to the main domain
    default_frontend_url = os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5000')
    
    session_params = {
        'payment_method_types': ['card'],
        'mode': 'payment',
        'success_url': os.environ.get('STRIPE_SUCCESS_URL', f'{default_frontend_url}/pages/join.html?success=true'),
        'cancel_url': os.environ.get('STRIPE_CANCEL_URL', f'{default_frontend_url}/pages/join.html?canceled=true'),
        'line_items': [],
        'metadata': {}
    }

    # Prefer a pre-created Price ID if provided (STRIPE_PRICE_ID / MEMBERSHIP_PRICE_ID).
    # Otherwise attach a price_data block referencing the existing Product ID.
    if MEMBERSHIP_PRICE_ID:
        session_params['line_items'] = [{
            'price': MEMBERSHIP_PRICE_ID,
            'quantity': 1
        }]
    else:
        # Use existing Product ID and create inline price_data referencing it.
        if not MEMBERSHIP_PRODUCT_ID:
            raise ValueError("STRIPE_PRODUCT_ID must be set when STRIPE_PRICE_ID is not provided")
        
        session_params['line_items'] = [{
            'price_data': {
                'currency': 'gbp',
                'unit_amount': MEMBERSHIP_AMOUNT,
                'product': MEMBERSHIP_PRODUCT_ID
            },
            'quantity': 1
        }]
    
    if user_id:
        session_params['metadata']['user_id'] = str(user_id)
    
    if customer_id:
        session_params['customer'] = customer_id
    elif email:
        session_params['customer_email'] = email
    
    try:
        session = stripe.checkout.Session.create(**session_params)
        return session
    except Exception as e:
        print(f"ERROR creating Stripe session: {type(e).__name__}: {e}")
        raise


def create_or_get_customer(email: str, name: str = None):
    """
    Create a new Stripe customer or retrieve existing one
    
    Returns:
        Stripe Customer object
    """
    if not STRIPE_SECRET_KEY:
        raise ValueError("Stripe is not configured.")
    
    # Check if customer exists
    customers = stripe.Customer.list(email=email, limit=1)
    if customers.data:
        return customers.data[0]
    
    # Create new customer
    customer_params = {'email': email}
    if name:
        customer_params['name'] = name
    
    customer = stripe.Customer.create(**customer_params)
    return customer


def verify_webhook_signature(payload: bytes, sig_header: str):
    """
    Verify Stripe webhook signature
    
    Returns:
        Event object if valid, None if invalid
    """
    if not STRIPE_WEBHOOK_SECRET:
        print("WARNING: STRIPE_WEBHOOK_SECRET not set. Webhook verification disabled.")
        return None
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError as e:
        print(f"Invalid payload: {e}")
        return None
    except Exception as e:
        # Catches SignatureVerificationError and other webhook errors
        print(f"Invalid signature or webhook error: {e}")
        return None


def get_payment_status(session_id: str):
    """
    Get payment status from Stripe Checkout session
    
    Returns:
        Payment status: 'pending', 'paid', 'failed', etc.
    """
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status
    except Exception as e:
        print(f"Error retrieving session: {e}")
        return None


