"""
WOVCC Authentication Helpers
Password hashing, JWT tokens, and authentication utilities
"""

import bcrypt
import jwt
from datetime import datetime, timedelta
import os
from functools import wraps
from flask import request, jsonify
from database import get_db, User

# JWT configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'change-this-secret-key-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days
JWT_REFRESH_EXPIRATION_DAYS = 30  # 30 days


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def generate_token(user_id: int, email: str, is_admin: bool = False, include_refresh: bool = True) -> dict:
    """Generate JWT access and refresh tokens"""
    now = datetime.now(timezone.utc)
    
    # Access token (short-lived)
    access_payload = {
        'user_id': user_id,
        'email': email,
        'is_admin': is_admin,
        'type': 'access',
        'exp': now + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': now
    }
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    result = {
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': JWT_EXPIRATION_HOURS * 3600  # in seconds
    }
    
    # Refresh token (long-lived) - optionally included
    if include_refresh:
        refresh_payload = {
            'user_id': user_id,
            'type': 'refresh',
            'exp': now + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS),
            'iat': now
        }
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        result['refresh_token'] = refresh_token
    
    return result


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expired'}
    except jwt.InvalidTokenError:
        return {'error': 'Invalid token'}


def get_token_from_request():
    """Extract JWT token from request header"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    # Format: "Bearer <token>"
    try:
        token = auth_header.split(' ')[1]
        return token
    except IndexError:
        return None


def get_refresh_token_from_request():
    """Extract refresh token from httpOnly cookie"""
    return request.cookies.get('refresh_token')


def get_current_user():
    """Get current authenticated user from request token"""
    token = get_token_from_request()
    if not token:
        return None
    
    payload = verify_token(token)
    if 'error' in payload:
        return None
    
    # Get user from database
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == payload['user_id']).first()
        if user:
            return user
        return None
    finally:
        db.close()


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        return f(user, *args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        if not user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        return f(user, *args, **kwargs)
    return decorated_function


