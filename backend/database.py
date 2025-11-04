"""
WOVCC Database Models and Connection
SQLite database for user management
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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




