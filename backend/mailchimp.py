"""
Mailchimp Integration Module
Handles newsletter subscriptions via Mailchimp API
"""

import os
import hashlib
import requests
import logging

logger = logging.getLogger(__name__)

# Mailchimp configuration
MAILCHIMP_API_KEY = os.environ.get('MAILCHIMP_API_KEY')
MAILCHIMP_LIST_ID = os.environ.get('MAILCHIMP_LIST_ID')

# Extract datacenter from API key (format: xxxxx-us19)
MAILCHIMP_SERVER = None
if MAILCHIMP_API_KEY:
    MAILCHIMP_SERVER = MAILCHIMP_API_KEY.split('-')[-1]


def is_mailchimp_configured():
    """Check if Mailchimp credentials are configured"""
    return bool(MAILCHIMP_API_KEY and MAILCHIMP_LIST_ID and MAILCHIMP_SERVER)


def get_subscriber_hash(email):
    """
    Get MD5 hash of lowercase email address
    This is required by Mailchimp API for member identification
    """
    return hashlib.md5(email.lower().encode()).hexdigest()


def subscribe_to_newsletter(email, name=None, merge_fields=None):
    """
    Subscribe an email address to the Mailchimp newsletter list
    
    Args:
        email (str): Email address to subscribe
        name (str, optional): Full name of subscriber
        merge_fields (dict, optional): Additional merge fields for Mailchimp
    
    Returns:
        dict: Result with 'success' boolean and 'message' string
    """
    if not is_mailchimp_configured():
        logger.warning("Mailchimp not configured - skipping newsletter subscription")
        return {
            'success': False,
            'message': 'Newsletter service not configured'
        }
    
    try:
        # Prepare the subscriber data
        subscriber_hash = get_subscriber_hash(email)
        url = f"https://{MAILCHIMP_SERVER}.api.mailchimp.com/3.0/lists/{MAILCHIMP_LIST_ID}/members/{subscriber_hash}"
        
        # First, check if the member already exists
        check_response = requests.get(
            url,
            auth=('anystring', MAILCHIMP_API_KEY),
            timeout=10
        )
        
        was_already_subscribed = False
        if check_response.status_code == 200:
            # Member exists - check their current status
            existing_member = check_response.json()
            existing_status = existing_member.get('status')
            
            if existing_status == 'subscribed':
                logger.info(f"Email {email} is already subscribed")
                was_already_subscribed = True
            else:
                logger.info(f"Email {email} exists with status: {existing_status}, updating to subscribed")
        
        # Build merge fields
        fields = merge_fields or {}
        if name and 'FNAME' not in fields:
            # Split name into first and last name
            name_parts = name.split(' ', 1)
            fields['FNAME'] = name_parts[0]
            if len(name_parts) > 1:
                fields['LNAME'] = name_parts[1]
        
        # Prepare request data
        # Using PUT with status_if_new ensures we create or update without duplicates
        data = {
            'email_address': email,
            'status_if_new': 'subscribed',  # Only subscribe if new
            'status': 'subscribed',  # Update status if already exists
        }
        
        if fields:
            data['merge_fields'] = fields
        
        # Make API request with basic auth
        response = requests.put(
            url,
            json=data,
            auth=('anystring', MAILCHIMP_API_KEY),
            timeout=10
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            status = result.get('status')
            
            if status == 'subscribed':
                if was_already_subscribed:
                    logger.info(f"Email {email} was already subscribed")
                    return {
                        'success': True,
                        'message': 'You are already subscribed to our newsletter',
                        'already_subscribed': True
                    }
                else:
                    logger.info(f"Successfully subscribed {email} to newsletter")
                    return {
                        'success': True,
                        'message': 'Successfully subscribed to newsletter',
                        'already_subscribed': False
                    }
            else:
                logger.info(f"Email {email} status: {status}")
                return {
                    'success': True,
                    'message': f'Newsletter subscription status: {status}',
                    'already_subscribed': True
                }
        
        elif response.status_code == 400:
            error_detail = response.json()
            title = error_detail.get('title', 'Unknown error')
            detail = error_detail.get('detail', '')
            
            # Check if already a member
            if 'is already a list member' in title.lower() or 'is already a list member' in detail.lower():
                logger.info(f"Email {email} is already subscribed")
                return {
                    'success': True,
                    'message': 'Email is already subscribed to newsletter',
                    'already_subscribed': True
                }
            
            logger.error(f"Mailchimp error for {email}: {title} - {detail}")
            return {
                'success': False,
                'message': f'Newsletter subscription error: {title}'
            }
        
        else:
            logger.error(f"Mailchimp API error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'message': f'Newsletter service error (code {response.status_code})'
            }
            
    except requests.exceptions.Timeout:
        logger.error(f"Mailchimp API timeout for {email}")
        return {
            'success': False,
            'message': 'Newsletter service timeout - please try again'
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Mailchimp request error for {email}: {e}")
        return {
            'success': False,
            'message': 'Newsletter service unavailable'
        }
    
    except Exception as e:
        logger.error(f"Unexpected error subscribing {email} to newsletter: {e}")
        return {
            'success': False,
            'message': 'An unexpected error occurred'
        }


def check_subscription_status(email):
    """
    Check if an email is subscribed to the newsletter
    
    Args:
        email (str): Email address to check
    
    Returns:
        dict: Result with 'subscribed' boolean and 'status' string
    """
    if not is_mailchimp_configured():
        return {
            'subscribed': False,
            'status': 'not_configured'
        }
    
    try:
        subscriber_hash = get_subscriber_hash(email)
        url = f"https://{MAILCHIMP_SERVER}.api.mailchimp.com/3.0/lists/{MAILCHIMP_LIST_ID}/members/{subscriber_hash}"
        
        response = requests.get(
            url,
            auth=('anystring', MAILCHIMP_API_KEY),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result.get('status')
            
            return {
                'subscribed': status == 'subscribed',
                'status': status
            }
        
        elif response.status_code == 404:
            # Email not found in list
            return {
                'subscribed': False,
                'status': 'not_found'
            }
        
        else:
            logger.error(f"Mailchimp status check error: {response.status_code}")
            return {
                'subscribed': False,
                'status': 'error'
            }
            
    except Exception as e:
        logger.error(f"Error checking subscription status for {email}: {e}")
        return {
            'subscribed': False,
            'status': 'error'
        }


def unsubscribe_from_newsletter(email):
    """
    Unsubscribe an email address from the newsletter
    
    Args:
        email (str): Email address to unsubscribe
    
    Returns:
        dict: Result with 'success' boolean and 'message' string
    """
    if not is_mailchimp_configured():
        return {
            'success': False,
            'message': 'Newsletter service not configured'
        }
    
    try:
        subscriber_hash = get_subscriber_hash(email)
        url = f"https://{MAILCHIMP_SERVER}.api.mailchimp.com/3.0/lists/{MAILCHIMP_LIST_ID}/members/{subscriber_hash}"
        
        # Update status to unsubscribed
        response = requests.patch(
            url,
            json={'status': 'unsubscribed'},
            auth=('anystring', MAILCHIMP_API_KEY),
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully unsubscribed {email} from newsletter")
            return {
                'success': True,
                'message': 'Successfully unsubscribed from newsletter'
            }
        
        elif response.status_code == 404:
            return {
                'success': True,
                'message': 'Email was not subscribed'
            }
        
        else:
            logger.error(f"Mailchimp unsubscribe error: {response.status_code}")
            return {
                'success': False,
                'message': 'Error unsubscribing from newsletter'
            }
            
    except Exception as e:
        logger.error(f"Error unsubscribing {email} from newsletter: {e}")
        return {
            'success': False,
            'message': 'An unexpected error occurred'
        }
