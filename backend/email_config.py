"""
Email Configuration Module
Provides centralized email sending functionality using Brevo SMTP.
"""

import os
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)


class EmailConfig:
    """Centralized email configuration using Brevo SMTP"""
    
    # Brevo SMTP Settings
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp-relay.brevo.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "9b575d001@smtp-brevo.com")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    
    # Email defaults
    DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@wickersleycricket.com")
    DEFAULT_SENDER_NAME = os.environ.get("MAIL_DEFAULT_SENDER_NAME", "WOVCC")
    CONTACT_RECIPIENT = os.environ.get("CONTACT_RECIPIENT", "info@wickersleycricket.com")
    
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
- View upcoming events: https://wovcc.co.uk/events
- Check match fixtures: https://wovcc.co.uk/matches
- Access your member area: https://wovcc.co.uk/members

If you have any questions, contact us at info@wickersleycricket.com

We look forward to seeing you at the club!

Best regards,
Wickersley Old Village Cricket Club
        """
        
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6; 
            color: #1a1a1a; 
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }}
        .container {{ 
            max-width: 600px; 
            margin: 30px auto; 
            background-color: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
        }}
        .header {{ 
            background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);
            color: white; 
            padding: 50px 40px; 
            text-align: center; 
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        .header p {{
            margin: 0;
            font-size: 16px;
            opacity: 0.95;
        }}
        .content {{ 
            padding: 40px 40px 30px 40px; 
            background-color: #ffffff; 
        }}
        .greeting {{
            font-size: 18px;
            color: #1a1a1a;
            margin-bottom: 20px;
        }}
        .success-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            color: #155724;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            margin: 20px 0;
            border-left: 4px solid #28a745;
        }}
        .receipt-box {{
            background-color: #ffffff;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 0;
            margin: 30px 0;
            overflow: hidden;
        }}
        .receipt-title {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #6c757d;
            font-weight: 600;
            margin: 0;
            padding: 20px 25px 15px 25px;
            background-color: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }}
        .receipt-items {{
            padding: 20px 25px;
        }}
        .receipt-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #f8f9fa;
            font-size: 15px;
        }}
        .receipt-item:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .receipt-item-label {{
            color: #495057;
            font-weight: 500;
            flex: 1;
            padding-right: 20px;
        }}
        .receipt-item-value {{
            font-weight: 600;
            color: #1a1a1a;
            text-align: right;
            white-space: nowrap;
        }}
        .receipt-total {{
            background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);
            color: white;
            padding: 20px 25px;
            font-size: 18px;
            overflow: hidden;
        }}
        .receipt-total-label {{
            font-weight: 600;
            display: inline-block;
            vertical-align: middle;
        }}
        .receipt-total-value {{
            font-size: 28px;
            font-weight: 700;
            white-space: nowrap;
            display: inline-block;
            float: right;
            vertical-align: middle;
        }}
        .section-title {{
            color: #1a5f5f;
            font-size: 20px;
            font-weight: 700;
            margin: 35px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 3px solid #d4a574;
        }}
        .links-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin: 20px 0 30px 0;
        }}
        .link-card {{
            display: block;
            background-color: #f8f9fa;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 20px 15px;
            text-align: center;
            text-decoration: none;
            transition: all 0.3s ease;
        }}
        .link-card:hover {{
            border-color: #1a5f5f;
            background-color: #ffffff;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(26, 95, 95, 0.15);
        }}
        .link-icon {{
            font-size: 32px;
            margin-bottom: 8px;
            display: block;
        }}
        .link-title {{
            font-weight: 600;
            color: #1a5f5f;
            font-size: 15px;
            margin: 0;
        }}
        .link-desc {{
            font-size: 13px;
            color: #6c757d;
            margin: 4px 0 0 0;
        }}
        .info-box {{
            background: linear-gradient(135deg, #e7f3ff 0%, #cfe8ff 100%);
            border-left: 4px solid #1a5f5f;
            padding: 20px;
            border-radius: 8px;
            margin: 25px 0;
        }}
        .info-box p {{
            margin: 0;
            color: #144a4a;
            font-size: 15px;
            line-height: 1.6;
        }}
        .footer {{ 
            padding: 30px 40px; 
            text-align: center; 
            font-size: 13px; 
            color: #6c757d;
            background-color: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }}
        .footer p {{
            margin: 6px 0;
        }}
        .footer-brand {{
            font-weight: 700;
            color: #1a5f5f;
            font-size: 15px;
        }}
        @media only screen and (max-width: 600px) {{
            .container {{
                margin: 10px;
                border-radius: 8px;
            }}
            .header {{
                padding: 40px 25px;
            }}
            .header h1 {{
                font-size: 26px;
            }}
            .content {{
                padding: 30px 25px 20px 25px;
            }}
            .links-grid {{
                grid-template-columns: 1fr;
            }}
            .receipt-title,
            .receipt-items,
            .receipt-total {{
                padding-left: 20px;
                padding-right: 20px;
            }}
            .footer {{
                padding: 25px 20px;
            }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f8f9fa; color: #1a1a1a;">
    <div class="container" style="background-color: #ffffff;">
        <div class="header" style="color: white; background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);">
            <h1 style="color: white;">🏏 Welcome to WOVCC!</h1>
            <p style="color: white;">Your membership is now active</p>
        </div>
        
        <div class="content" style="color: #1a1a1a; background-color: #ffffff;">
            <p class="greeting" style="color: #1a1a1a;">Dear {to_name},</p>
            
            <div style="text-align: center;">
                <div class="success-badge" style="color: #155724;">
                    ✓ Membership Active
                </div>
            </div>
            
            <p style="font-size: 16px; margin: 25px 0; color: #495057;">
                Thank you for joining Wickersley Old Village Cricket Club! Your payment has been processed and your membership is now active.
            </p>
            
            <div class="receipt-box">
                <div class="receipt-title">Payment Receipt</div>
                <div class="receipt-items">
                    <div class="receipt-item">
                        <span class="receipt-item-label">Annual Membership</span>
                        <span class="receipt-item-value">{currency_symbol}{base_membership:.2f}</span>
                    </div>
                    {('<div class="receipt-item"><span class="receipt-item-label">Additional Extra Card</span><span class="receipt-item-value">' + currency_symbol + f'{extra_card_price:.2f}</span></div>') if has_spouse_card else ''}
                    {('<div class="receipt-item"><span class="receipt-item-label">Valid Until</span><span class="receipt-item-value">' + membership_expiry + '</span></div>') if membership_expiry else ''}
                </div>
                <div class="receipt-total">
                    <div class="receipt-total-label">Total Paid</div>
                    <div class="receipt-total-value">{currency_symbol}{amount_paid:.2f}</div>
                </div>
            </div>
            
            <h2 class="section-title">What's Next?</h2>
            
            <div class="links-grid">
                <a href="https://wovcc.co.uk/events" class="link-card">
                    <span class="link-icon">📅</span>
                    <p class="link-title">View Events</p>
                    <p class="link-desc">Upcoming club events</p>
                </a>
                <a href="https://wovcc.co.uk/matches" class="link-card">
                    <span class="link-icon">🏏</span>
                    <p class="link-title">Match Fixtures</p>
                    <p class="link-desc">See the schedule</p>
                </a>
                <a href="https://wovcc.co.uk/members" class="link-card">
                    <span class="link-icon">👤</span>
                    <p class="link-title">Member Area</p>
                    <p class="link-desc">Access your account</p>
                </a>
                <a href="https://wovcc.co.uk/contact" class="link-card">
                    <span class="link-icon">✉️</span>
                    <p class="link-title">Contact Us</p>
                    <p class="link-desc">Get in touch</p>
                </a>
            </div>
            
            <div class="info-box">
                <p style="color: #144a4a;">
                    Need help? If you have any questions about your membership, feel free to contact us at <a href="mailto:info@wickersleycricket.com" style="color: #1a5f5f; font-weight: 600; text-decoration: none;">info@wickersleycricket.com</a>
                </p>
            </div>
            
            <p style="margin-top: 30px; font-size: 15px; color: #495057;">
                We look forward to seeing you at the club!
            </p>
        </div>
        
        <div class="footer" style="color: #6c757d; background-color: #f8f9fa;">
            <p class="footer-brand" style="color: #1a5f5f;">Wickersley Old Village Cricket Club</p>
            <p style="color: #6c757d;">This is an automated confirmation email.</p>
            <p style="margin-top: 15px; font-size: 12px; color: #6c757d;">
                © 2025 WOVCC. All rights reserved.
            </p>
        </div>
    </div>
</body>
</html>
        """
        
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
        
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6; 
            color: #1a1a1a; 
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }}
        .container {{ 
            max-width: 600px; 
            margin: 30px auto; 
            background-color: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
        }}
        .header {{ 
            background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);
            color: white; 
            padding: 50px 40px; 
            text-align: center; 
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        .header p {{
            margin: 0;
            font-size: 16px;
            opacity: 0.95;
        }}
        .content {{ 
            padding: 40px 40px 30px 40px; 
            background-color: #ffffff; 
        }}
        .greeting {{
            font-size: 18px;
            color: #1a1a1a;
            margin-bottom: 20px;
        }}
        .success-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            color: #155724;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            margin: 20px 0;
            border-left: 4px solid #28a745;
        }}
        .receipt-box {{
            background-color: #ffffff;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 0;
            margin: 30px 0;
            overflow: hidden;
        }}
        .receipt-title {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #6c757d;
            font-weight: 600;
            margin: 0;
            padding: 20px 25px 15px 25px;
            background-color: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }}
        .receipt-items {{
            padding: 20px 25px;
        }}
        .receipt-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #f8f9fa;
            font-size: 15px;
        }}
        .receipt-item:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .receipt-item-label {{
            color: #495057;
            font-weight: 500;
            flex: 1;
            padding-right: 20px;
        }}
        .receipt-item-value {{
            font-weight: 600;
            color: #1a1a1a;
            text-align: right;
            white-space: nowrap;
        }}
        .receipt-total {{
            background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);
            color: white;
            padding: 20px 25px;
            font-size: 18px;
            overflow: hidden;
        }}
        .receipt-total-label {{
            font-weight: 600;
            display: inline-block;
            vertical-align: middle;
        }}
        .receipt-total-value {{
            font-size: 28px;
            font-weight: 700;
            white-space: nowrap;
            display: inline-block;
            float: right;
            vertical-align: middle;
        }}
        .info-box {{
            background: linear-gradient(135deg, #e7f3ff 0%, #cfe8ff 100%);
            border-left: 4px solid #1a5f5f;
            padding: 20px;
            border-radius: 8px;
            margin: 25px 0;
        }}
        .info-box p {{
            margin: 0;
            color: #144a4a;
            font-size: 15px;
            line-height: 1.6;
        }}
        .footer {{ 
            padding: 30px 40px; 
            text-align: center; 
            font-size: 13px; 
            color: #6c757d;
            background-color: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }}
        .footer p {{
            margin: 6px 0;
        }}
        .footer-brand {{
            font-weight: 700;
            color: #1a5f5f;
            font-size: 15px;
        }}
        @media only screen and (max-width: 600px) {{
            .container {{
                margin: 10px;
                border-radius: 8px;
            }}
            .header {{
                padding: 40px 25px;
            }}
            .header h1 {{
                font-size: 26px;
            }}
            .content {{
                padding: 30px 25px 20px 25px;
            }}
            .receipt-title,
            .receipt-items,
            .receipt-total {{
                padding-left: 20px;
                padding-right: 20px;
            }}
            .footer {{
                padding: 25px 20px;
            }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f8f9fa; color: #1a1a1a;">
    <div class="container" style="background-color: #ffffff;">
        <div class="header" style="color: white; background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);">
            <h1 style="color: white;">✅ Purchase Confirmed</h1>
            <p style="color: white;">Additional Extra Card Activated</p>
        </div>
        
        <div class="content" style="color: #1a1a1a; background-color: #ffffff;">
            <p class="greeting" style="color: #1a1a1a;">Dear {to_name},</p>
            
            <div style="text-align: center;">
                <div class="success-badge" style="color: #155724;">
                    ✓ Card Activated
                </div>
            </div>
            
            <p style="font-size: 16px; margin: 25px 0; color: #495057;">
                Thank you for purchasing an additional extra card for your WOVCC membership! Your payment has been processed and the card has been activated.
            </p>
            
            <div class="receipt-box">
                <div class="receipt-title">Payment Receipt</div>
                <div class="receipt-items">
                    <div class="receipt-item">
                        <span class="receipt-item-label">Additional Extra Card</span>
                        <span class="receipt-item-value">{currency_symbol}{amount_paid:.2f}</span>
                    </div>
                </div>
                <div class="receipt-total">
                    <div class="receipt-total-label">Total Paid</div>
                    <div class="receipt-total-value">{currency_symbol}{amount_paid:.2f}</div>
                </div>
            </div>
            
            <div class="info-box">
                <p style="color: #144a4a;">
                    Your additional card is now linked to your membership account. If you have any questions, feel free to contact us at <a href="mailto:info@wickersleycricket.com" style="color: #1a5f5f; font-weight: 600; text-decoration: none;">info@wickersleycricket.com</a>
                </p>
            </div>
            
            <p style="margin-top: 30px; font-size: 15px; color: #495057;">
                Thank you for your continued support of the club!
            </p>
        </div>
        
        <div class="footer" style="color: #6c757d; background-color: #f8f9fa;">
            <p class="footer-brand" style="color: #1a5f5f;">Wickersley Old Village Cricket Club</p>
            <p style="color: #6c757d;">This is an automated confirmation email.</p>
            <p style="margin-top: 15px; font-size: 12px; color: #6c757d;">
                © 2025 WOVCC. All rights reserved.
            </p>
        </div>
    </div>
</body>
</html>
        """
        
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
        
        body = f"""
Dear {to_name},

Congratulations! Your WOVCC membership is now active.

You can now:
- Access the members' area on our website
- View upcoming matches and events
- Receive club updates and newsletters

Visit our website: https://wovcc.co.uk

If you have any questions, please contact us at info@wovcc.co.uk

We look forward to seeing you at the club!

Best regards,
West of Valley Cricket Club
        """
        
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: 'Inter', Arial, sans-serif; 
            line-height: 1.6; 
            color: #1a1a1a; 
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }}
        .container {{ 
            max-width: 600px; 
            margin: 20px auto; 
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{ 
            background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);
            color: white; 
            padding: 40px 30px; 
            text-align: center; 
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .content {{ 
            padding: 40px 30px; 
            background-color: #ffffff; 
        }}
        .features {{ 
            background-color: #f8f9fa; 
            padding: 24px; 
            margin: 24px 0; 
            border-radius: 6px;
            border-left: 4px solid #1a5f5f;
        }}
        .features h3 {{
            color: #1a5f5f;
            margin-top: 0;
            margin-bottom: 16px;
        }}
        .features ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .features li {{
            margin-bottom: 8px;
            color: #1a1a1a;
        }}
        .button {{ 
            display: inline-block; 
            padding: 14px 32px; 
            background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);
            color: white !important; 
            text-decoration: none; 
            border-radius: 6px;
            font-weight: 500;
        }}
        .footer {{ 
            padding: 30px; 
            text-align: center; 
            background-color: #f8f9fa;
            font-size: 12px; 
            color: #6c757d;
        }}
        a {{ color: #1a5f5f; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to WOVCC!</h1>
        </div>
        <div class="content">
            <p>Dear {to_name},</p>
            <p><strong>Congratulations! Your WOVCC membership is now active.</strong></p>
            <div class="features">
                <h3>You can now:</h3>
                <ul>
                    <li>Access the members' area on our website</li>
                    <li>View upcoming matches and events</li>
                    <li>Receive club updates and newsletters</li>
                </ul>
            </div>
            <p style="text-align: center;">
                <a href="https://wovcc.co.uk" class="button">Visit Our Website</a>
            </p>
            <p>If you have any questions, please contact us at <a href="mailto:info@wickersleycricket.com">info@wickersleycricket.com</a></p>
            <p><strong>We look forward to seeing you at the club!</strong></p>
        </div>
        <div class="footer">
            <p><strong>Wickersley Old Village Cricket Club</strong></p>
        </div>
    </div>
</body>
</html>
        """
        
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
        message: str
    ) -> bool:
        """
        Send contact form notification to club admin.
        
        Args:
            from_name: Name of person contacting
            from_email: Email of person contacting
            subject: Contact form subject
            message: Contact form message
            
        Returns:
            bool: True if sent successfully
        """
        email_subject = f"[WOVCC Contact] {subject}"
        
        body = f"""
New contact form submission from WOVCC website:

Name: {from_name}
Email: {from_email}

Subject: {subject}

Message:
{message}
        """
        
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: 'Inter', Arial, sans-serif; 
            line-height: 1.6; 
            color: #1a1a1a; 
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }}
        .container {{ 
            max-width: 600px; 
            margin: 20px auto; 
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{ 
            background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);
            color: white; 
            padding: 30px; 
        }}
        .header h2 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .content {{ 
            padding: 30px; 
        }}
        .info {{ 
            background-color: #f8f9fa; 
            padding: 20px; 
            margin: 20px 0; 
            border-left: 4px solid #1a5f5f;
            border-radius: 4px;
        }}
        .info p {{
            margin: 8px 0;
        }}
        .message {{ 
            background-color: #ffffff; 
            padding: 24px; 
            margin: 20px 0; 
            border: 1px solid #e9ecef;
            border-radius: 6px;
        }}
        .message h3 {{
            color: #1a5f5f;
            margin-top: 0;
            margin-bottom: 16px;
        }}
        a {{ color: #1a5f5f; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>📧 New Contact Form Submission</h2>
        </div>
        <div class="content">
            <div class="info">
                <p><strong>From:</strong> {from_name}</p>
                <p><strong>Email:</strong> <a href="mailto:{from_email}">{from_email}</a></p>
                <p><strong>Subject:</strong> {subject}</p>
            </div>
            <div class="message">
                <h3>Message:</h3>
                <p style="white-space: pre-wrap;">{message.replace(chr(10), '<br>')}</p>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
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
        
        body = f"""
Dear {to_name},

We received a request to reset your password for your WOVCC account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour for security reasons.

If you did not request a password reset, please ignore this email and your password will remain unchanged.

Best regards,
West of Valley Cricket Club
        """
        
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: 'Inter', Arial, sans-serif; 
            line-height: 1.6; 
            color: #1a1a1a; 
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }}
        .container {{ 
            max-width: 600px; 
            margin: 20px auto; 
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{ 
            background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);
            color: white; 
            padding: 40px 30px; 
            text-align: center; 
        }}
        .header h1 {{
            margin: 0;
            font-size: 26px;
            font-weight: 600;
        }}
        .content {{ 
            padding: 40px 30px; 
        }}
        .button {{ 
            display: inline-block; 
            padding: 14px 32px; 
            background: linear-gradient(135deg, #1a5f5f 0%, #144a4a 100%);
            color: white !important; 
            text-decoration: none; 
            border-radius: 6px; 
            margin: 24px 0;
            font-weight: 500;
        }}
        .url-fallback {{
            font-size: 12px; 
            color: #6c757d;
            word-break: break-all;
            background-color: #f8f9fa;
            padding: 12px;
            border-radius: 4px;
            border-left: 3px solid #d4a574;
        }}
        .warning {{ 
            background-color: #fff3cd; 
            padding: 16px; 
            border-left: 4px solid #d4a574; 
            margin: 24px 0;
            border-radius: 4px;
        }}
        .warning p {{
            margin: 0;
        }}
        .footer {{ 
            padding: 30px; 
            text-align: center; 
            font-size: 12px; 
            color: #6c757d;
            background-color: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Dear {to_name},</p>
            <p>We received a request to reset your password for your WOVCC account.</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset My Password</a>
            </p>
            <div class="url-fallback">
                Or copy and paste this link into your browser:<br>
                {reset_url}
            </div>
            <p><strong>⏱️ This link will expire in 1 hour for security reasons.</strong></p>
            <div class="warning">
                <p><strong>⚠️ If you did not request a password reset, please ignore this email and your password will remain unchanged.</strong></p>
            </div>
        </div>
        <div class="footer">
            <p><strong>Wickersley Cricket Club</strong></p>
            <p>This is an automated email. Please do not reply.</p>
        </div>
    </div>
</body>
</html>
        """
        
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
