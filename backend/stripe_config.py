"""
WOVCC Stripe Configuration
Handles Stripe payment integration
"""

import stripe
import os

# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')  # Use test key: sk_test_...
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')  # Use test key: pk_test_...
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')  # For webhook verification
MEMBERSHIP_PRICE_ID = os.environ.get('STRIPE_PRICE_ID', '')  # Price ID for £15 membership
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
    
    session_params = {
        'payment_method_types': ['card'],
        'mode': 'payment',
        'success_url': os.environ.get('STRIPE_SUCCESS_URL', 'http://localhost:5000/pages/join.html?success=true'),
        'cancel_url': os.environ.get('STRIPE_CANCEL_URL', 'http://localhost:5000/pages/join.html?canceled=true'),
        'line_items': [{
            'price_data': {
                'currency': 'gbp',
                'product_data': {
                    'name': 'WOVCC Annual Membership',
                    'description': 'Annual membership for Wickersley Old Village Cricket Club'
                },
                'unit_amount': MEMBERSHIP_AMOUNT,
            },
            'quantity': 1,
        }],
        'metadata': {}
    }
    
    if user_id:
        session_params['metadata']['user_id'] = str(user_id)
    
    if customer_id:
        session_params['customer'] = customer_id
    elif email:
        session_params['customer_email'] = email
    
    session = stripe.checkout.Session.create(**session_params)
    return session


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
    except stripe.error.SignatureVerificationError as e:
        print(f"Invalid signature: {e}")
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

