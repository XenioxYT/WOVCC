"""
Email Configuration Module
Provides centralized email sending functionality using Brevo SMTP.
"""

import os
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template, has_app_context
import logging

logger = logging.getLogger(__name__)

# Base site URL for email links (configurable via .env)
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://wovcc.xeniox.uk").rstrip('/')


def render_email_template(template_name: str, **context):
    """
    Safely render an email template, creating app context if needed.
    
    Args:
        template_name: Template path relative to templates directory
        **context: Template context variables
        
    Returns:
        str: Rendered HTML template
    """
    context = {'site_base_url': SITE_BASE_URL, **context}
    if has_app_context():
        # Already in app context, render directly
        return render_template(template_name, **context)
    else:
        # Need to create app context
        from flask import Flask
        app = Flask(__name__)
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        with app.app_context():
            return render_template(template_name, **context)


class EmailConfig:
    """Centralized email configuration using Brevo SMTP"""
    
    # Brevo SMTP Settings
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp-relay.brevo.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    
    # Email defaults
    DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@wickersleycricket.com")
    DEFAULT_SENDER_NAME = os.environ.get("MAIL_DEFAULT_SENDER_NAME", "WOVCC")
    CONTACT_RECIPIENT = os.environ.get("CONTACT_RECIPIENT", "wovcc10@gmail.com")
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if SMTP is properly configured"""
        return bool(cls.SMTP_HOST and cls.SMTP_USERNAME and cls.SMTP_PASSWORD)
    
    @classmethod
    def get_smtp_connection(cls):
        """
        Create and return an authenticated SMTP connection.
        
        Returns:
            smtplib.SMTP: Authenticated SMTP connection
            
        Raises:
            RuntimeError: If SMTP is not configured
            smtplib.SMTPException: If connection or authentication fails
        """
        if not cls.is_configured():
            raise RuntimeError(
                "SMTP not configured. Please set SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD environment variables."
            )
        
        try:
            server = smtplib.SMTP(cls.SMTP_HOST, cls.SMTP_PORT, timeout=10)
            
            if cls.SMTP_USE_TLS:
                server.starttls()
            
            server.login(cls.SMTP_USERNAME, cls.SMTP_PASSWORD)
            logger.info(f"SMTP connection established to {cls.SMTP_HOST}")
            return server
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP connection failed: {e}", exc_info=True)
            raise
    
    @classmethod
    def send_email(
        cls,
        to_email: str,
        subject: str,
        body: str,
        body_html: str = None,
        from_email: str = None,
        from_name: str = None,
        reply_to: str = None
    ) -> bool:
        """
        Send an email using Brevo SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text email body
            body_html: Optional HTML email body
            from_email: Sender email (defaults to DEFAULT_SENDER)
            from_name: Sender name (defaults to DEFAULT_SENDER_NAME)
            reply_to: Optional reply-to address
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not cls.is_configured():
            logger.error("Cannot send email: SMTP not configured")
            return False
        
        try:
            # Set defaults
            from_email = from_email or cls.DEFAULT_SENDER
            from_name = from_name or cls.DEFAULT_SENDER_NAME
            
            # Create message
            if body_html:
                msg = MIMEMultipart('alternative')
                # Set headers FIRST
                msg['Subject'] = subject
                msg['From'] = f"{from_name} <{from_email}>"
                msg['To'] = to_email
                if reply_to:
                    msg['Reply-To'] = reply_to
                
                # Then attach parts (plain text first, then HTML)
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
                msg.attach(MIMEText(body_html, 'html', 'utf-8'))
            else:
                msg = EmailMessage()
                msg.set_content(body)
                msg['Subject'] = subject
                msg['From'] = f"{from_name} <{from_email}>"
                msg['To'] = to_email
                if reply_to:
                    msg['Reply-To'] = reply_to
            
            # Send email
            with cls.get_smtp_connection() as server:
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            return False
    
    @classmethod
    def send_welcome_receipt_email(
        cls, 
        to_email: str, 
        to_name: str, 
        amount_paid: float,
        currency: str = 'GBP',
        has_spouse_card: bool = False,
        membership_expiry: str = None
    ) -> bool:
        """
        Send welcome and receipt email after successful payment.
        
        Args:
            to_email: Recipient email
            to_name: Recipient name
            amount_paid: Amount paid (in major currency units, e.g., 50.00)
            currency: Currency code (default: GBP)
            has_spouse_card: Whether spouse card was included
            membership_expiry: Membership expiry date string
            
        Returns:
            bool: True if sent successfully
        """
        # Format currency symbol
        currency_symbol = '£' if currency == 'GBP' else '$'
        
        # Calculate line items
        base_membership = 15.00 if currency == 'GBP' else 15.00  # First year membership
        extra_card_price = 5.00 if currency == 'GBP' else 5.00
        
        subject = f"Welcome to WOVCC - Your Membership is Active!"
        
        # Plain text version
        body = f"""
Dear {to_name},

Welcome to Wickersley Old Village Cricket Club!

Thank you for joining. Your payment has been processed and your membership is now active.

PAYMENT RECEIPT
------------------
Annual Membership: {currency_symbol}{base_membership:.2f}
{'Additional Extra Card: ' + currency_symbol + f'{extra_card_price:.2f}' if has_spouse_card else ''}
------------------
Total Paid: {currency_symbol}{amount_paid:.2f}
{'Valid Until: ' + membership_expiry if membership_expiry else ''}

WHAT'S NEXT?
- View upcoming events: {SITE_BASE_URL}/events
- Check match fixtures: {SITE_BASE_URL}/matches
- Access your member area: {SITE_BASE_URL}/members

If you have any questions, contact us at info@wickersleycricket.com

We look forward to seeing you at the club!

Best regards,
Wickersley Old Village Cricket Club
        """
        
        # HTML version using template
        body_html = render_email_template(
            'emails/welcome_receipt.html',
            name=to_name,
            currency_symbol=currency_symbol,
            base_membership_price=f"{base_membership:.2f}",
            extra_card_price=f"{extra_card_price:.2f}",
            amount_paid=f"{amount_paid:.2f}",
            has_spouse_card=has_spouse_card,
            membership_expiry=membership_expiry
        )
        
        return cls.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            body_html=body_html
        )
    
    @classmethod
    def send_extra_card_receipt_email(
        cls, 
        to_email: str, 
        to_name: str, 
        amount_paid: float,
        currency: str = 'GBP'
    ) -> bool:
        """
        Send receipt email after purchasing an additional extra card separately.
        
        Args:
            to_email: Recipient email
            to_name: Recipient name
            amount_paid: Amount paid (in major currency units, e.g., 5.00)
            currency: Currency code (default: GBP)
            
        Returns:
            bool: True if sent successfully
        """
        # Format currency symbol
        currency_symbol = '£' if currency == 'GBP' else '$'
        
        subject = f"WOVCC - Additional Extra Card Purchase Confirmed"
        
        # Plain text version
        body = f"""
Dear {to_name},

Thank you for purchasing an additional extra card for your WOVCC membership!

PAYMENT RECEIPT
------------------
Additional Extra Card: {currency_symbol}{amount_paid:.2f}
------------------
Total Paid: {currency_symbol}{amount_paid:.2f}

Your additional card has been activated and linked to your membership account.

If you have any questions, contact us at info@wickersleycricket.com

Best regards,
Wickersley Old Village Cricket Club
        """
        
        # HTML version using template
        body_html = render_email_template(
            'emails/extra_card_receipt.html',
            name=to_name,
            currency_symbol=currency_symbol,
            amount_paid=f"{amount_paid:.2f}"
        )
        
        return cls.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            body_html=body_html
        )
    
    @classmethod
    def send_welcome_email(cls, to_email: str, to_name: str) -> bool:
        """
        Send welcome email to new member.
        
        Args:
            to_email: Recipient email
            to_name: Recipient name
            
        Returns:
            bool: True if sent successfully
        """
        subject = "Welcome to WOVCC - Membership Activated!"
        
        # Plain text version
        body = f"""
Dear {to_name},

Congratulations! Your WOVCC membership is now active.

You can now:
- Access the members' area on our website
- View upcoming matches and events
- Receive club updates and newsletters

Visit our website: {SITE_BASE_URL}

If you have any questions, please contact us at {cls.CONTACT_RECIPIENT}

We look forward to seeing you at the club!

Best regards,
Wickersley Old Village Cricket Club
        """
        
        # HTML version using template
        body_html = render_email_template(
            'emails/welcome.html',
            name=to_name
        )
        
        return cls.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            body_html=body_html
        )
    
    @classmethod
    def send_contact_notification(
        cls,
        from_name: str,
        from_email: str,
        subject: str,
        message: str,
        from_phone: str = None
    ) -> bool:
        """
        Send contact form notification to club admin.
        
        Args:
            from_name: Name of person contacting
            from_email: Email of person contacting
            subject: Contact form subject
            message: Contact form message
            from_phone: Phone number (optional)
            
        Returns:
            bool: True if sent successfully
        """
        email_subject = f"[WOVCC Contact] {subject}"
        
        # Plain text version
        phone_line = f"Phone: {from_phone}\n" if from_phone else ""
        body = f"""
New contact form submission from WOVCC website:

Name: {from_name}
Email: {from_email}
{phone_line}
Subject: {subject}

Message:
{message}
        """
        
        # HTML version using template
        body_html = render_email_template(
            'emails/contact_notification.html',
            from_name=from_name,
            from_email=from_email,
            from_phone=from_phone,
            subject=subject,
            message=message
        )
        
        return cls.send_email(
            to_email=cls.CONTACT_RECIPIENT,
            subject=email_subject,
            body=body,
            body_html=body_html,
            reply_to=from_email
        )
    
    @classmethod
    def send_password_reset_email(cls, to_email: str, to_name: str, reset_url: str) -> bool:
        """
        Send password reset email.
        
        Args:
            to_email: Recipient email
            to_name: Recipient name
            reset_url: Password reset URL with token
            
        Returns:
            bool: True if sent successfully
        """
        subject = "WOVCC - Password Reset Request"
        
        # Plain text version
        body = f"""
Dear {to_name},

We received a request to reset your password for your WOVCC account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour for security reasons.

If you did not request a password reset, please ignore this email and your password will remain unchanged.

Best regards,
Wickersley Old Village Cricket Club
        """
        
        # HTML version using template
        body_html = render_email_template(
            'emails/password_reset.html',
            name=to_name,
            reset_url=reset_url
        )
        
        return cls.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            body_html=body_html
        )


# Convenience functions for backward compatibility
def send_email(to_email: str, subject: str, body: str, **kwargs) -> bool:
    """Send email using EmailConfig"""
    return EmailConfig.send_email(to_email, subject, body, **kwargs)


def is_email_configured() -> bool:
    """Check if email is configured"""
    return EmailConfig.is_configured()
