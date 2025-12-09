"""
Unit tests for Stripe checkout configuration to ensure contact details
are required and collected for membership flows.
"""
from unittest.mock import patch, MagicMock

import stripe

import stripe_config


def test_checkout_session_requires_contact_details():
    """
    Verify create_checkout_session configures phone + billing address collection
    and customer creation/update so we can sync contact details via webhooks.
    """
    stripe_config.STRIPE_SECRET_KEY = 'sk_test_dummy'
    stripe_config.MEMBERSHIP_PRICE_ID = 'price_test'
    stripe_config.MEMBERSHIP_PRODUCT_ID = 'prod_test'
    stripe.api_key = stripe_config.STRIPE_SECRET_KEY

    fake_session = MagicMock(id='cs_test', url='https://example.com/checkout')

    with patch('stripe.checkout.Session.create', return_value=fake_session) as mock_create:
        session = stripe_config.create_checkout_session(
            email='test@example.com',
            user_id=123
        )

        assert session == fake_session

        # Ensure the session was created with required contact collection
        kwargs = mock_create.call_args.kwargs
        assert kwargs['billing_address_collection'] == 'required'
        assert kwargs['phone_number_collection']['enabled'] is True
        assert kwargs['customer_creation'] == 'always'
        assert kwargs['customer_update']['address'] == 'auto'
        assert kwargs['customer_update']['name'] == 'auto'
        assert kwargs['metadata']['user_id'] == '123'

