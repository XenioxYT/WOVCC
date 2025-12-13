"""
WOVCC Stripe Configuration
Handles Stripe payment integration
"""

import stripe
import os
import json
from urllib.parse import quote
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

# Additional card addon configuration (extra physical card for spouse/partner)
SPOUSE_CARD_PRICE_ID = os.environ.get('STRIPE_SPOUSE_CARD_PRICE_ID', '')  # Price ID for £5 additional card (price_...)
SPOUSE_CARD_PRODUCT_ID = os.environ.get('STRIPE_SPOUSE_CARD_PRODUCT_ID')  # Product ID for additional card (prod_...)
SPOUSE_CARD_AMOUNT = 500  # £5.00 in pence - extra physical card sharing same membership account

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    print("WARNING: STRIPE_SECRET_KEY not set. Stripe functionality will be disabled.")


def create_checkout_session(customer_id: str = None, email: str = None, user_id: int = None, include_spouse_card: bool = False, activation_token: str = None):
    """
    Create a Stripe Checkout session for membership payment
    
    Args:
        customer_id: Existing Stripe customer ID (optional)
        email: Customer email (for new signups)
        user_id: User ID to include in metadata (optional)
        include_spouse_card: Whether to include spouse card addon (optional)
        activation_token: Secure token for account activation (optional)
    
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
    
    # Build success URL with activation token if provided (secure activation)
    # NOTE: Stripe allows query parameters in success_url and preserves them
    success_url = os.environ.get('STRIPE_SUCCESS_URL', f'{default_frontend_url}/join/activate')
    if activation_token:
        # Append activation token as URL parameter
        # URL encode the token to handle special characters (- and _ are safe in URLs)
        encoded_token = quote(activation_token, safe='-_')
        separator = '&' if '?' in success_url else '?'
        success_url = f'{success_url}{separator}token={encoded_token}'
    
    session_params = {
        'payment_method_types': ['card'],
        'mode': 'payment',
        'success_url': success_url,
        'cancel_url': os.environ.get('STRIPE_CANCEL_URL', f'{default_frontend_url}/join/cancel'),
        'line_items': [],
        'metadata': {},
        # WOVCC Brand Colors
        'ui_mode': 'hosted',
        'custom_text': {
            'submit': {
                'message': 'Join Wickersley Old Village Cricket Club'
            }
        }
    }

    # Build line items array
    line_items = []
    
    # Prefer a pre-created Price ID if provided (STRIPE_PRICE_ID / MEMBERSHIP_PRICE_ID).
    # Otherwise attach a price_data block referencing the existing Product ID.
    if MEMBERSHIP_PRICE_ID:
        line_items.append({
            'price': MEMBERSHIP_PRICE_ID,
            'quantity': 1
        })
    else:
        # Use existing Product ID and create inline price_data referencing it.
        if not MEMBERSHIP_PRODUCT_ID:
            raise ValueError("STRIPE_PRODUCT_ID must be set when STRIPE_PRICE_ID is not provided")
        
        line_items.append({
            'price_data': {
                'currency': 'gbp',
                'unit_amount': MEMBERSHIP_AMOUNT,
                'product': MEMBERSHIP_PRODUCT_ID
            },
            'quantity': 1
        })
    
    # Add additional card if requested (extra physical card for spouse/partner)
    if include_spouse_card:
        if SPOUSE_CARD_PRICE_ID:
            line_items.append({
                'price': SPOUSE_CARD_PRICE_ID,
                'quantity': 1
            })
        elif SPOUSE_CARD_PRODUCT_ID:
            line_items.append({
                'price_data': {
                    'currency': 'gbp',
                    'unit_amount': SPOUSE_CARD_AMOUNT,
                    'product': SPOUSE_CARD_PRODUCT_ID
                },
                'quantity': 1
            })
        else:
            print("WARNING: Additional card requested but STRIPE_SPOUSE_CARD_PRICE_ID or STRIPE_SPOUSE_CARD_PRODUCT_ID not set")
    
    session_params['line_items'] = line_items
    
    if user_id:
        session_params['metadata']['user_id'] = str(user_id)
    
    # Handle customer attachment - cannot use both 'customer' and 'customer_creation'
    if customer_id:
        # Existing customer - attach to their record
        session_params['customer'] = customer_id
        session_params['customer_update'] = {
            'address': 'auto',
            'name': 'auto'
        }
    else:
        # New customer - create one and collect billing details
        session_params['customer_creation'] = 'always'
        session_params['billing_address_collection'] = 'required'
        session_params['phone_number_collection'] = {'enabled': True}
        if email:
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


def create_spouse_card_checkout_session(customer_id: str = None, email: str = None, user_id: int = None):
    """
    Create a Stripe Checkout session for additional card only (for existing members)
    This creates a second physical card that shares the same membership account.
    
    Args:
        customer_id: Existing Stripe customer ID (optional)
        email: Customer email
        user_id: User ID to include in metadata (required)
    
    Returns:
        Stripe Checkout Session object
    """
    if not STRIPE_SECRET_KEY:
        raise ValueError("Stripe is not configured. Please set STRIPE_SECRET_KEY environment variable.")
    
    if not user_id:
        raise ValueError("user_id is required for spouse card purchase")
    
    # Ensure Stripe API key is set
    if not stripe.api_key:
        stripe.api_key = STRIPE_SECRET_KEY
    
    # Determine the base URL for frontend redirects
    default_frontend_url = os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5000')
    
    # Use specific URLs for spouse card purchase (don't use env vars as those are for new signups)
    session_params = {
        'payment_method_types': ['card'],
        'mode': 'payment',
        'success_url': f'{default_frontend_url}/membership?spouse_card=success',
        'cancel_url': f'{default_frontend_url}/membership?spouse_card=cancel',
        'line_items': [],
        'metadata': {
            'user_id': str(user_id),
            'spouse_card_only': 'true'
        },
        'ui_mode': 'hosted',
        'custom_text': {
            'submit': {
                'message': 'Add Additional Card to Your Membership'
            }
        }
    }
    
    # Add additional card line item
    if SPOUSE_CARD_PRICE_ID:
        session_params['line_items'] = [{
            'price': SPOUSE_CARD_PRICE_ID,
            'quantity': 1
        }]
    elif SPOUSE_CARD_PRODUCT_ID:
        session_params['line_items'] = [{
            'price_data': {
                'currency': 'gbp',
                'unit_amount': SPOUSE_CARD_AMOUNT,
                'product': SPOUSE_CARD_PRODUCT_ID
            },
            'quantity': 1
        }]
    else:
        raise ValueError("STRIPE_SPOUSE_CARD_PRICE_ID or STRIPE_SPOUSE_CARD_PRODUCT_ID must be set")
    
    # For existing customers, attach to their customer record (no need to collect address/phone again)
    # For new customers (shouldn't happen for spouse card, but handle gracefully), create a new customer
    if customer_id:
        session_params['customer'] = customer_id
        session_params['customer_update'] = {
            'address': 'auto',
            'name': 'auto'
        }
        # Don't require address/phone collection - they already provided this during initial signup
    else:
        # Fallback: if somehow no customer_id, create a new customer and collect details
        session_params['customer_creation'] = 'always'
        session_params['billing_address_collection'] = 'required'
        session_params['phone_number_collection'] = {'enabled': True}
        if email:
            session_params['customer_email'] = email
    
    try:
        session = stripe.checkout.Session.create(**session_params)
        return session
    except Exception as e:
        print(f"ERROR creating Stripe additional card session: {type(e).__name__}: {e}")
        raise


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


def delete_stripe_customer(customer_id: str):
    """
    Delete a Stripe customer (for GDPR Right to Erasure)
    
    This permanently deletes the customer from Stripe, which:
    - Removes all customer data from Stripe
    - Cancels all active subscriptions
    - Deletes all payment methods
    
    Args:
        customer_id: Stripe customer ID (starts with 'cus_')
    
    Returns:
        True if successful, False otherwise
    """
    if not STRIPE_SECRET_KEY:
        print("WARNING: STRIPE_SECRET_KEY not set. Cannot delete customer.")
        return False
    
    if not customer_id:
        print("WARNING: No customer_id provided for deletion")
        return False
    
    # Ensure Stripe API key is set
    if not stripe.api_key:
        stripe.api_key = STRIPE_SECRET_KEY
    
    try:
        # Delete the customer from Stripe
        # This will automatically cancel all subscriptions and remove all data
        stripe.Customer.delete(customer_id)
        print(f"Successfully deleted Stripe customer: {customer_id}")
        return True
    except stripe.error.InvalidRequestError as e:
        # Customer doesn't exist or already deleted
        print(f"Stripe customer not found or already deleted: {customer_id} - {e}")
        return True  # Consider it a success since the goal (customer deleted) is achieved
    except Exception as e:
        print(f"ERROR deleting Stripe customer {customer_id}: {type(e).__name__}: {e}")
        return False


