# backend/auth.py

from flask import request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from functools import wraps
from models import User, db
from datetime import datetime

def login_required(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check for token in Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'status': 'error', 'message': 'Missing authorization token'}), 401
        
        try:
            # Extract token
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            # Verify token
            from flask_jwt_extended import decode_token
            decoded = decode_token(token)
            request.user_id = decoded.get('sub')
            request.user_role = decoded.get('role')
        except Exception as e:
            return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 401
        
        return f(*args, **kwargs)
    return decorated

def role_required(allowed_roles):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            # Get user from database
            user = User.query.get(request.user_id)
            if not user:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404
            
            if user.role not in allowed_roles:
                return jsonify({'status': 'error', 'message': f'Insufficient permissions. Required: {allowed_roles}'}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_current_user():
    """Get current user from JWT token"""
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
        return User.query.get(user_id)
    except:
        return None