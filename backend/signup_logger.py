"""
Signup Activity Model and Weekly Report System
Tracks all new member signups and generates weekly summary reports.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from database import Base, engine, get_db
from datetime import datetime, timezone, timedelta
from email_config import EmailConfig
import logging

logger = logging.getLogger(__name__)


class SignupActivity(Base):
    """Log every signup with payment details for weekly reporting"""
    __tablename__ = 'signup_activities'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # Link to User table
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    has_spouse_card = Column(Boolean, default=False)
    amount_paid = Column(Float, nullable=False)  # Amount in dollars/pounds
    currency = Column(String(10), default='GBP')
    stripe_session_id = Column(String(255), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    membership_type = Column(String(100), default='Annual Member')
    signup_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    newsletter_subscribed = Column(Boolean, default=False)
    
    # Weekly report tracking
    included_in_report = Column(Boolean, default=False, index=True)
    report_sent_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'has_spouse_card': self.has_spouse_card,
            'amount_paid': self.amount_paid,
            'currency': self.currency,
            'membership_type': self.membership_type,
            'signup_date': self.signup_date.isoformat() if self.signup_date else None,
            'newsletter_subscribed': self.newsletter_subscribed,
            'included_in_report': self.included_in_report,
            'report_sent_date': self.report_sent_date.isoformat() if self.report_sent_date else None
        }


def init_signup_activity_table():
    """Initialize the signup_activities table"""
    Base.metadata.create_all(bind=engine)
    logger.info("SignupActivity table created/verified")


def log_signup(
    user_id: int,
    name: str,
    email: str,
    has_spouse_card: bool,
    amount_paid: float,
    currency: str = 'GBP',
    stripe_session_id: str = None,
    stripe_customer_id: str = None,
    newsletter_subscribed: bool = False
) -> bool:
    """
    Log a new signup to the database.
    
    Args:
        user_id: The created user's ID
        name: User's name
        email: User's email
        has_spouse_card: Whether they purchased spouse card
        amount_paid: Amount paid in currency units (e.g., 50.00 for £50)
        currency: Currency code (default: GBP)
        stripe_session_id: Stripe checkout session ID
        stripe_customer_id: Stripe customer ID
        newsletter_subscribed: Whether subscribed to newsletter
        
    Returns:
        bool: True if logged successfully
    """
    try:
        db = next(get_db())
        try:
            activity = SignupActivity(
                user_id=user_id,
                name=name,
                email=email,
                has_spouse_card=has_spouse_card,
                amount_paid=amount_paid,
                currency=currency,
                stripe_session_id=stripe_session_id,
                stripe_customer_id=stripe_customer_id,
                newsletter_subscribed=newsletter_subscribed
            )
            db.add(activity)
            db.commit()
            logger.info(f"Logged signup for {email} - £{amount_paid} - Additional card: {has_spouse_card}")
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log signup for {email}: {e}", exc_info=True)
        return False


def get_weekly_signups(include_reported: bool = False):
    """
    Get all signups from the past week.
    
    Args:
        include_reported: If True, include signups already included in reports
        
    Returns:
        list: List of SignupActivity records
    """
    try:
        db = next(get_db())
        try:
            # Calculate date range (last 7 days)
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=7)
            
            query = db.query(SignupActivity).filter(
                SignupActivity.signup_date >= week_ago
            )
            
            if not include_reported:
                query = query.filter(SignupActivity.included_in_report == False)
            
            signups = query.order_by(SignupActivity.signup_date.desc()).all()
            return signups
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to get weekly signups: {e}", exc_info=True)
        return []


def generate_weekly_report_email(signups: list) -> tuple:
    """
    Generate HTML and text email for weekly signup report.
    
    Args:
        signups: List of SignupActivity records
        
    Returns:
        tuple: (subject, body_text, body_html)
    """
    if not signups:
        return None, None, None
    
    # Calculate totals
    total_signups = len(signups)
    total_revenue = sum(s.amount_paid for s in signups)
    spouse_cards = sum(1 for s in signups if s.has_spouse_card)
    newsletter_subs = sum(1 for s in signups if s.newsletter_subscribed)
    
    # Get date range
    oldest_signup = min(s.signup_date for s in signups)
    newest_signup = max(s.signup_date for s in signups)
    
    subject = f"Weekly Signup Report - {total_signups} New Members (£{total_revenue:.2f})"
    
    # Plain text version
    body_text = f"""
WOVCC Weekly Signup Report
{'=' * 60}

Report Period: {oldest_signup.strftime('%d %B %Y')} - {newest_signup.strftime('%d %B %Y')}

Summary:
- Total New Members: {total_signups}
- Total Revenue: £{total_revenue:.2f}
- Additional Cards: {spouse_cards}
- Newsletter Subscriptions: {newsletter_subs}

{'=' * 60}

Member Details:
"""
    
    for i, signup in enumerate(signups, 1):
        body_text += f"""
{i}. {signup.name}
   Email: {signup.email}
   Amount Paid: £{signup.amount_paid:.2f}
   Additional Card: {'Yes' if signup.has_spouse_card else 'No'}
   Newsletter: {'Yes' if signup.newsletter_subscribed else 'No'}
   Signup Date: {signup.signup_date.strftime('%d %B %Y at %H:%M')}
   {'─' * 60}
"""
    
    body_text += f"""
{'=' * 60}

This report was automatically generated.
To view member details, log in to the admin dashboard.
"""
    
    # HTML version
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
            background-color: #f8f9fa;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 800px;
            margin: 20px auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
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
            letter-spacing: -0.02em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.95;
            font-size: 14px;
        }}
        .summary {{
            display: flex;
            flex-wrap: wrap;
            padding: 20px;
            background-color: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }}
        .summary-item {{
            flex: 1;
            min-width: 150px;
            padding: 15px;
            text-align: center;
        }}
        .summary-item h3 {{
            margin: 0;
            font-size: 32px;
            color: #1a5f5f;
            font-weight: 600;
        }}
        .summary-item p {{
            margin: 5px 0 0 0;
            color: #6c757d;
            font-size: 14px;
        }}
        .content {{
            padding: 30px;
        }}
        .member-card {{
            background-color: #f8f9fa;
            border-left: 4px solid #1a5f5f;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 6px;
        }}
        .member-card h3 {{
            margin: 0 0 12px 0;
            color: #1a5f5f;
            font-size: 20px;
            font-weight: 600;
        }}
        .member-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-top: 12px;
        }}
        .detail-item {{
            padding: 8px 0;
        }}
        .detail-label {{
            font-weight: 600;
            color: #6c757d;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .detail-value {{
            color: #1a1a1a;
            font-size: 14px;
            margin-top: 4px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-yes {{
            background-color: #d4edda;
            color: #155724;
        }}
        .badge-no {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .footer {{
            padding: 25px 30px;
            text-align: center;
            background-color: #f8f9fa;
            border-top: 1px solid #e9ecef;
            font-size: 12px;
            color: #6c757d;
        }}
        .footer p {{
            margin: 6px 0;
        }}
        .revenue {{
            color: #28a745;
            font-weight: 600;
        }}
        a {{
            color: #1a5f5f;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏏 Weekly Signup Report</h1>
            <p>{oldest_signup.strftime('%d %B %Y')} - {newest_signup.strftime('%d %B %Y')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-item">
                <h3>{total_signups}</h3>
                <p>New Members</p>
            </div>
            <div class="summary-item">
                <h3 class="revenue">£{total_revenue:.2f}</h3>
                <p>Total Revenue</p>
            </div>
            <div class="summary-item">
                <h3>{spouse_cards}</h3>
                <p>Additional Cards</p>
            </div>
            <div class="summary-item">
                <h3>{newsletter_subs}</h3>
                <p>Newsletter Subs</p>
            </div>
        </div>
        
        <div class="content">
            <h2 style="color: #1a5f5f; margin-top: 0; font-weight: 600;">Member Details</h2>
"""
    
    for i, signup in enumerate(signups, 1):
        body_html += f"""
            <div class="member-card">
                <h3>{i}. {signup.name}</h3>
                <div class="member-details">
                    <div class="detail-item">
                        <div class="detail-label">Email</div>
                        <div class="detail-value">{signup.email}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Amount Paid</div>
                        <div class="detail-value revenue">£{signup.amount_paid:.2f}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Additional Card</div>
                        <div class="detail-value">
                            <span class="badge {'badge-yes' if signup.has_spouse_card else 'badge-no'}">
                                {'Yes' if signup.has_spouse_card else 'No'}
                            </span>
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Newsletter</div>
                        <div class="detail-value">
                            <span class="badge {'badge-yes' if signup.newsletter_subscribed else 'badge-no'}">
                                {'Yes' if signup.newsletter_subscribed else 'No'}
                            </span>
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Signup Date</div>
                        <div class="detail-value">{signup.signup_date.strftime('%d %B %Y at %H:%M')}</div>
                    </div>
                </div>
            </div>
"""
    
    body_html += """
        </div>
        
        <div class="footer">
            <p><strong>Wickersley Cricket Club</strong></p>
            <p>This report was automatically generated by the WOVCC membership system.</p>
            <p>To view full member details, log in to the admin dashboard at <a href="https://wovcc.co.uk/admin">wovcc.co.uk/admin</a></p>
        </div>
    </div>
</body>
</html>
"""
    
    return subject, body_text, body_html


def send_weekly_report(recipient_email: str = None) -> bool:
    """
    Generate and send weekly signup report.
    
    Args:
        recipient_email: Email to send report to (defaults to CONTACT_RECIPIENT)
        
    Returns:
        bool: True if report sent successfully
    """
    try:
        # Get unreported signups from the past week
        signups = get_weekly_signups(include_reported=False)
        
        if not signups:
            logger.info("No new signups this week - skipping report")
            return True
        
        # Generate report email
        subject, body_text, body_html = generate_weekly_report_email(signups)
        
        if not subject:
            logger.warning("Failed to generate report email")
            return False
        
        # Send email
        recipient = recipient_email or EmailConfig.CONTACT_RECIPIENT
        success = EmailConfig.send_email(
            to_email=recipient,
            subject=subject,
            body=body_text,
            body_html=body_html,
            from_name="WOVCC Membership System"
        )
        
        if success:
            # Mark signups as reported
            db = next(get_db())
            try:
                now = datetime.now(timezone.utc)
                signup_ids = [signup.id for signup in signups]
                db.query(SignupActivity).filter(
                    SignupActivity.id.in_(signup_ids)
                ).update({
                    'included_in_report': True,
                    'report_sent_date': now
                }, synchronize_session=False)
                db.commit()
                logger.info(f"Weekly report sent successfully to {recipient} - {len(signups)} signups")
            finally:
                db.close()
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to send weekly report: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    # Initialize table when run directly
    init_signup_activity_table()
    print("SignupActivity table initialized")
