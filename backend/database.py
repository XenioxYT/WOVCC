"""
WOVCC Database Models and Connection
SQLite database for user management
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///wovcc.db')
Base = declarative_base()

# Create engine
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    """User model for authentication and membership"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    activation_token = Column(String(255), unique=True, index=True, nullable=True)  # Temporary token for first-time activation (cleared after use)
    membership_tier = Column(String(100), default='Social Member')
    is_member = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    newsletter = Column(Boolean, default=False)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    payment_status = Column(String(50), default='pending')  # pending, active, expired, cancelled
    has_spouse_card = Column(Boolean, default=False)  # Whether user has purchased spouse card addon
    membership_start_date = Column(DateTime, nullable=True)  # When membership started
    membership_expiry_date = Column(DateTime, nullable=True)  # When membership expires
    join_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_events = relationship('Event', back_populates='creator', foreign_keys='Event.created_by_user_id')
    event_interests = relationship('EventInterest', back_populates='user', foreign_keys='EventInterest.user_id')
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary, optionally excluding sensitive data"""
        data = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'membership_tier': self.membership_tier,
            'is_member': self.is_member,
            'is_admin': self.is_admin,
            'newsletter': self.newsletter,
            'payment_status': self.payment_status,
            'has_spouse_card': self.has_spouse_card,
            'membership_start_date': self.membership_start_date.isoformat() if self.membership_start_date else None,
            'membership_expiry_date': self.membership_expiry_date.isoformat() if self.membership_expiry_date else None,
            'join_date': self.join_date.isoformat() if self.join_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            data['stripe_customer_id'] = self.stripe_customer_id
        
        return data


class PendingRegistration(Base):
    """Temporary pending registration stored until payment completes"""
    __tablename__ = 'pending_registrations'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    activation_token = Column(String(255), unique=True, index=True, nullable=False)  # Secure token for account activation
    newsletter = Column(Boolean, default=False)
    include_spouse_card = Column(Boolean, default=False)  # Whether user wants spouse card addon
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'newsletter': self.newsletter,
            'include_spouse_card': self.include_spouse_card,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Event(Base):
    """Event model for club events"""
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    short_description = Column(String(255), nullable=False)
    long_description = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    time = Column(String(50), nullable=True)
    image_url = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    
    # Recurring event fields
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(50), nullable=True)  # 'daily', 'weekly', 'monthly'
    recurrence_end_date = Column(DateTime, nullable=True)
    parent_event_id = Column(Integer, ForeignKey('events.id'), nullable=True, index=True)  # For tracking recurring instances
    
    # Publishing and tracking
    is_published = Column(Boolean, default=False, index=True)
    interested_count = Column(Integer, default=0)
    
    # Metadata
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship('User', back_populates='created_events', foreign_keys=[created_by_user_id])
    interests = relationship('EventInterest', back_populates='event', cascade='all, delete-orphan')
    
    # Self-referential relationship for recurring events
    parent_event = relationship('Event', remote_side=[id], backref='recurring_instances')
    
    def to_dict(self, include_sensitive=False):
        """Convert event to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'short_description': self.short_description,
            'long_description': self.long_description,
            'date': self.date.isoformat() if self.date else None,
            'date_display': self.date.strftime('%A, %d %B %Y') if self.date else None,
            'time': self.time,
            'image_url': self.image_url,
            'location': self.location,
            'category': self.category,
            'is_recurring': self.is_recurring,
            'recurrence_pattern': self.recurrence_pattern,
            'recurrence_end_date': self.recurrence_end_date.isoformat() if self.recurrence_end_date else None,
            'parent_event_id': self.parent_event_id,
            'is_published': self.is_published,
            'interested_count': self.interested_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            data['created_by_user_id'] = self.created_by_user_id
        
        return data


class EventInterest(Base):
    """Track which users are interested in which events"""
    __tablename__ = 'event_interests'
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Nullable for anonymous interest
    user_email = Column(String(255), nullable=True)  # For non-members
    user_name = Column(String(255), nullable=True)  # For non-members
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event = relationship('Event', back_populates='interests')
    user = relationship('User', back_populates='event_interests', foreign_keys=[user_id])
    
    def to_dict(self):
        """Convert event interest to dictionary"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'user_name': self.user_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ContentSnippet(Base):
    """Content snippets for CMS - editable text content on the site"""
    __tablename__ = 'content_snippets'
    
    key = Column(String(100), primary_key=True)  # e.g., 'homepage_welcome'
    content = Column(Text, nullable=False)  # The actual content
    description = Column(String(255), nullable=True)  # Description of what this snippet is for
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert content snippet to dictionary"""
        return {
            'key': self.key,
            'content': self.content,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Sponsor(Base):
    """Sponsor model for club sponsors displayed in footer"""
    __tablename__ = 'sponsors'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    logo_url = Column(String(500), nullable=False)  # WebP image path
    website_url = Column(String(500), nullable=True)
    display_order = Column(Integer, default=0, index=True)  # Manual ordering (lower = first)
    is_active = Column(Boolean, default=True, index=True)  # Show/hide toggle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert sponsor to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'logo_url': self.logo_url,
            'website_url': self.website_url,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LiveConfig(Base):
    """Live match streaming configuration - stored in database for persistence across container restarts"""
    __tablename__ = 'live_config'
    
    id = Column(Integer, primary_key=True, default=1)  # Single row configuration
    is_live = Column(Boolean, default=False, nullable=False)
    livestream_url = Column(String(500), default='', nullable=False)
    selected_match_data = Column(Text, nullable=True)  # JSON string for match object
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert live config to dictionary"""
        import json
        selected_match = None
        if self.selected_match_data:
            try:
                selected_match = json.loads(self.selected_match_data)
            except json.JSONDecodeError:
                selected_match = None
        
        return {
            'is_live': self.is_live,
            'livestream_url': self.livestream_url,
            'selected_match': selected_match,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create or update from dictionary"""
        import json
        selected_match_data = None
        if data.get('selected_match'):
            selected_match_data = json.dumps(data['selected_match'])
        
        return cls(
            id=1,  # Always use id=1 for single-row config
            is_live=data.get('is_live', False),
            livestream_url=data.get('livestream_url', ''),
            selected_match_data=selected_match_data
        )


class ScrapedData(Base):
    """
    Cached cricket data from Play-Cricket scraper.
    Stored in database for persistence across container restarts.
    Implements stale-while-revalidate pattern: old data is preserved if scraper fails.
    """
    __tablename__ = 'scraped_data'
    
    id = Column(Integer, primary_key=True, default=1)  # Single row for all data
    teams_data = Column(Text, nullable=True)  # JSON array of teams
    fixtures_data = Column(Text, nullable=True)  # JSON array of fixtures
    results_data = Column(Text, nullable=True)  # JSON array of results
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scrape_success = Column(Boolean, default=True)  # Track if last scrape was successful
    scrape_error_message = Column(Text, nullable=True)  # Store error message if scrape failed
    
    def to_dict(self):
        """Convert scraped data to dictionary format matching the old JSON file structure"""
        import json
        
        teams = []
        fixtures = []
        results = []
        
        if self.teams_data:
            try:
                teams = json.loads(self.teams_data)
            except json.JSONDecodeError:
                pass
        
        if self.fixtures_data:
            try:
                fixtures = json.loads(self.fixtures_data)
            except json.JSONDecodeError:
                pass
        
        if self.results_data:
            try:
                results = json.loads(self.results_data)
            except json.JSONDecodeError:
                pass
        
        return {
            'teams': teams,
            'fixtures': fixtures,
            'results': results,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'last_scrape_success': self.last_scrape_success,
            'scrape_error_message': self.scrape_error_message
        }
    
    @classmethod
    def update_from_scrape(cls, db_session, teams=None, fixtures=None, results=None, 
                           success=True, error_message=None):
        """
        Update scraped data in database with stale-while-revalidate logic.
        If scrape failed, keeps old data and logs the error.
        """
        import json
        
        # Get or create the single row
        data_row = db_session.query(cls).filter(cls.id == 1).first()
        if not data_row:
            data_row = cls(id=1)
            db_session.add(data_row)
        
        # Only update data if scrape was successful
        if success:
            if teams is not None:
                data_row.teams_data = json.dumps(teams)
            if fixtures is not None:
                data_row.fixtures_data = json.dumps(fixtures)
            if results is not None:
                data_row.results_data = json.dumps(results)
            data_row.last_scrape_success = True
            data_row.scrape_error_message = None
        else:
            # Scrape failed - keep old data, log error
            data_row.last_scrape_success = False
            data_row.scrape_error_message = error_message
        
        data_row.last_updated = datetime.utcnow()
        db_session.commit()
        
        return data_row


def init_db():
    """Initialize database - create all tables"""
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("Database initialized successfully")
    except Exception as e:
        # Handle race condition where multiple workers try to create tables simultaneously
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            logger.info("Database tables already exist (race condition handled)")
        else:
            raise


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_from_localstorage():
    """Migrate users from localStorage to database (one-time migration)"""
    # This will be called manually if needed
    # Reads from a JSON file or directly from frontend localStorage export
    pass


if __name__ == '__main__':
    # Initialize database when run directly
    init_db()
    print(f"Database created at: {DATABASE_URL}")




