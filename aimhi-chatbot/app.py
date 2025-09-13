"""
Simplified Supabase-Enabled Flask Application
===========================================
Reduced try/except blocks and simplified error handling.
"""

import os
import logging
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# --- Local Imports ---
from config.auth_middleware import require_auth, get_current_user_id
from config.supabase_client import test_connection
from database.repository import (
    create_session, get_session, save_message, get_chat_history,
    accept_response, get_user_sessions, record_risk_detection,
    record_intent_classification
)

load_dotenv()

# --- Configuration ---
FLASK_ENV = os.getenv("FLASK_ENV", "production")
IS_PROD = (FLASK_ENV == "production")
SECRET_KEY = os.getenv("SECRET_KEY")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
RATE_LIMIT_STORAGE = os.getenv("RATE_LIMIT_STORAGE", "memory://")
RATE_LIMIT_DAY = int(os.getenv("RATE_LIMIT_DAY", "200"))
RATE_LIMIT_HOUR = int(os.getenv("RATE_LIMIT_HOUR", "50"))
origins_env = os.getenv("CORS_ORIGINS", "").strip()

# --- Logging Configuration ---
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app")

# --- Flask App Initialization ---
app = Flask(__name__)

if IS_PROD and not SECRET_KEY:
    logger.warning("SECRET_KEY not set, using generated key")
app.secret_key = SECRET_KEY or os.urandom(24).hex()

# --- CORS Configuration ---
if IS_PROD:
    ORIGINS = [o.strip() for o in origins_env.split(",") if o.strip()]
    if not ORIGINS:
        raise SystemExit("CORS_ORIGINS must be set in production")
else:
    ORIGINS = [r"http://localhost:\d+", r"http://127\.0\.0\.1:\d+"]

cors_config = {
    "origins": ORIGINS,
    "supports_credentials": True,
    "allow_headers": ["Content-Type", "Authorization"],
    "methods": ["GET", "POST"],
    "max_age": 86400,
}

CORS(app, resources={
    r"/api/.*": cors_config,
    r"/auth/.*": cors_config,
    r"/sessions": cors_config,
    r"/sessions/*": cors_config,
    r"/health": cors_config,
    r"/": cors_config
}, vary_header=True)

# --- Rate Limiting ---
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMIT_DAY} per day", f"{RATE_LIMIT_HOUR} per hour"],
    storage_uri=RATE_LIMIT_STORAGE
)

# --- Database Connection Test ---
if not test_connection() and IS_PROD:
    raise SystemExit("Startup aborted: Database connection failed.")

logger.info("✅ Flask app initialized with Supabase backend")

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.route('/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """Register a new user with Supabase Auth"""
    from config.supabase_client import supabase_anon
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    response = supabase_anon.auth.sign_up({
        'email': email,
        'password': password
    })
    
    if response.user:
        logger.info(f"User registered: {response.user.id}")
        return jsonify({
            'message': 'Registration successful',
            'user_id': response.user.id,
            'access_token': response.session.access_token if response.session else None,
            'refresh_token': response.session.refresh_token if response.session else None
        }), 201
    
    return jsonify({'error': 'Registration failed'}), 400

@app.route('/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Login with email and password"""
    from config.supabase_client import supabase_anon
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    response = supabase_anon.auth.sign_in_with_password({
        'email': email,
        'password': password
    })
    
    if response.user and response.session:
        logger.info(f"User logged in: {response.user.id}")
        return jsonify({
            'message': 'Login successful',
            'user_id': response.user.id,
            'access_token': response.session.access_token,
            'refresh_token': response.session.refresh_token,
            'expires_at': response.session.expires_at
        }), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout current user"""
    from config.supabase_client import supabase_anon
    
    supabase_anon.auth.sign_out()
    user_id = get_current_user_id()
    logger.info(f"User logged out: {user_id}")
    
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/auth/me', methods=['GET'])
@require_auth
def get_user():
    """Get current user info"""
    user_id = get_current_user_id()
    return jsonify({
        'user_id': user_id,
        'authenticated': True
    }), 200

# ==================== SESSION MANAGEMENT ENDPOINTS ====================

@app.route('/sessions', methods=['POST'])
@require_auth
@limiter.limit("20 per minute")
def create_user_session():
    """Create a new chat session for authenticated user"""
    user_id = get_current_user_id()
    data = request.get_json() or {}
    
    fsm_state = data.get('fsm_state', 'welcome')
    session_id = create_session(user_id=user_id, fsm_state=fsm_state)
    
    if session_id:
        logger.info(f"Created session {session_id} for user {user_id}")
        return jsonify({
            'session_id': session_id,
            'fsm_state': fsm_state,
            'status': 'active'
        }), 201
    
    return jsonify({'error': 'Failed to create session'}), 500

@app.route('/sessions/<session_id>', methods=['GET'])
@require_auth
def get_user_session(session_id):
    """Get session info if user owns it"""
    user_id = get_current_user_id()
    session = get_session(user_id, session_id)
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify(session), 200

@app.route('/sessions/<session_id>/messages', methods=['POST'])
@require_auth
@limiter.limit("30 per minute")
def send_user_message(session_id):
    """Send a message in a chat session and get bot response"""
    user_id = get_current_user_id()
    data = request.get_json()
    
    if not data or not data.get('message'):
        return jsonify({'error': 'Message text required'}), 400
    
    message = data.get('message').strip()
    if len(message) > 1000:
        return jsonify({'error': 'Message too long (max 1000 characters)'}), 400
    
    # Save user message
    user_msg_id = save_message(
        user_id=user_id,
        session_id=session_id,
        role='user',
        message=message,
        message_type=data.get('message_type', 'text'),
        meta=data.get('meta')
    )
    
    if not user_msg_id:
        return jsonify({'error': 'Failed to save user message'}), 500
    
    # Import router and process message
    from core.router import route_message
    bot_response = route_message(user_id, session_id, message)
    
    # Save bot response
    bot_msg_id = save_message(
        user_id=user_id,
        session_id=session_id,
        role='bot',
        message=bot_response,
        message_type='fsm_response'
    )
    
    return jsonify({
        'user_message_id': user_msg_id,
        'bot_message_id': bot_msg_id,
        'reply': bot_response
    }), 200

@app.route('/sessions/<session_id>/messages', methods=['GET'])
@require_auth
def get_user_messages(session_id):
    """Get chat history for a session"""
    user_id = get_current_user_id()
    limit = min(int(request.args.get('limit', 50)), 200)
    
    messages = get_chat_history(user_id, session_id, limit)
    if messages is None:
        return jsonify({'error': 'Session not found or access denied'}), 403
    
    return jsonify(messages), 200

@app.route('/sessions/<session_id>/accept', methods=['POST'])
@require_auth
def accept_user_response(session_id):
    """Accept a specific response as final for a FSM step"""
    user_id = get_current_user_id()
    data = request.get_json()
    
    if not data or 'step' not in data or 'message_id' not in data:
        return jsonify({'error': 'step and message_id required'}), 400
    
    success = accept_response(
        user_id=user_id,
        session_id=session_id,
        step=data['step'],
        message_id=int(data['message_id'])
    )
    
    if success:
        return jsonify({'message': 'Response accepted'}), 200
    else:
        return jsonify({'error': 'Failed to accept response'}), 500

@app.route('/sessions', methods=['GET'])
@require_auth
def list_sessions():
    """Get all sessions for the authenticated user"""
    user_id = get_current_user_id()
    limit = min(int(request.args.get('limit', 20)), 50)
    
    sessions = get_user_sessions(user_id, limit)
    return jsonify(sessions), 200

# ==================== BASIC ENDPOINTS ====================

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')

@app.route("/health")
def health_check():
    """Health check endpoint"""
    db_connected = test_connection()
    
    return jsonify({
        "status": "ok" if db_connected else "degraded",
        "database": "connected" if db_connected else "disconnected",
        "auth": "supabase"
    }), 200 if db_connected else 503

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Not Found"}), 404

@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"error": "Method Not Allowed"}), 405

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(error=f"Rate limit exceeded: {e.description}"), 429

@app.errorhandler(500)
def internal_server_error(e):
    logger.error("Unhandled 500: %s", e, exc_info=True)
    return jsonify({"error": "Internal Server Error"}), 500

# ==================== SECURITY HEADERS ====================

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    csp = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self' https://*.supabase.co; "
        "frame-ancestors 'none';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response

# ==================== DEVELOPMENT SERVER ====================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = (not IS_PROD)
    logger.info("Starting Flask server on http://0.0.0.0:%d (Debug: %s)", port, debug_mode)
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
