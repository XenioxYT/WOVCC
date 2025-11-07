"""
WOVCC Database Models and Connection
SQLite database for user management
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

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
    membership_tier = Column(String(100), default='Social Member')
    is_member = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    newsletter = Column(Boolean, default=False)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    payment_status = Column(String(50), default='pending')  # pending, active, expired, cancelled
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
    newsletter = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'newsletter': self.newsletter,
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


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")


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




