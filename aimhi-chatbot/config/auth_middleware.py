"""
Simplified JWT Authentication Middleware
======================================
Reduced try/except blocks and simplified error handling.
"""

import jwt
import logging
import os
from functools import wraps
from flask import request, jsonify, g
from typing import Optional
from config.supabase_client import JWT_SECRET

logger = logging.getLogger(__name__)

def extract_user_from_token() -> Optional[str]:
    """
    Extract user_id from JWT token in Authorization header.
    Returns user_id if valid, None if no token, raises Exception if invalid.
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return None
        
    if not auth_header.startswith('Bearer '):
        raise Exception("Invalid authorization header format. Use 'Bearer <token>'")
    
    token = auth_header.split(' ')[1]
    
    dev_mode = os.getenv('FLASK_ENV', 'production') != 'production'
    decoded = None
    # Prefer verified decode when secret is available
    if JWT_SECRET:
        try:
            decoded = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=['HS256'],
                audience='authenticated',
                options={"verify_iss": False}
            )
        except Exception as e:
            # In development, allow unverified decode to avoid local setup blockers
            if dev_mode:
                logger.warning(f"JWT verify failed in dev, using unverified decode: {e}")
                decoded = jwt.decode(token, options={
                    'verify_signature': False,
                    'verify_aud': False,
                    'verify_iss': False
                })
            else:
                raise
    else:
        if dev_mode:
            decoded = jwt.decode(token, options={
                'verify_signature': False,
                'verify_aud': False,
                'verify_iss': False
            })
        else:
            raise Exception("JWT secret not configured")
    
    user_id = decoded.get('sub')
    if not user_id:
        raise Exception("No user ID in token")
        
    # Store in Flask g for easy access
    g.user_id = user_id
    return user_id

def require_auth(f):
    """
    Decorator that requires valid JWT authentication.
    Adds user_id to request context.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            user_id = extract_user_from_token()
            if not user_id:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Please provide a valid Authorization header with Bearer token'
                }), 401
                
            # Make user_id available to the route
            request.user_id = user_id
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Authentication failed',
                'message': 'Token has expired'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'error': 'Authentication failed', 
                'message': 'Invalid token'
            }), 401
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return jsonify({
                'error': 'Authentication failed',
                'message': str(e)
            }), 401
            
    return decorated

def optional_auth(f):
    """
    Decorator that optionally extracts user from JWT if present.
    Does not require authentication but will validate if token is provided.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            user_id = extract_user_from_token()
            request.user_id = user_id  # May be None
            return f(*args, **kwargs)
        except Exception:
            # If token is provided but invalid, still reject
            auth_header = request.headers.get('Authorization')
            if auth_header:
                return jsonify({
                    'error': 'Invalid authentication',
                    'message': 'Token provided but invalid'
                }), 401
            # No token provided, continue without auth
            request.user_id = None
            return f(*args, **kwargs)
            
    return decorated

def get_current_user_id() -> str:
    """
    Helper function to get current user ID from request context.
    Raises Exception if no user is authenticated.
    """
    user_id = getattr(request, 'user_id', None)
    if not user_id:
        raise Exception("No authenticated user")
    return user_id
