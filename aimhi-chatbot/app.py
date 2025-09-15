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
from pathlib import Path
from werkzeug.middleware.proxy_fix import ProxyFix

# --- Local Imports ---
from config.auth_middleware import require_auth, get_current_user_id
from config.supabase_client import test_connection
from database.repository import (
    create_session, get_session, save_message, get_chat_history,
    accept_response, get_user_sessions, record_risk_detection,
    record_intent_classification
)
from database.repository import delete_session as repo_delete_session

# Only load .env automatically in development to avoid leaking dev values in prod
_dev_guess = os.getenv("FLASK_ENV", "production") != "production"
if _dev_guess:
    load_dotenv(dotenv_path=str(Path(__file__).with_name(".env")), override=True)

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
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

if IS_PROD and not SECRET_KEY:
    raise SystemExit("SECRET_KEY must be set in production")
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
    "methods": ["GET", "POST", "DELETE"],
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
# Prefer Redis when available (e.g., on Render) to avoid per-process memory limits
REDIS_URL = os.getenv("REDIS_URL")
if (not RATE_LIMIT_STORAGE or RATE_LIMIT_STORAGE == "memory://") and REDIS_URL:
    RATE_LIMIT_STORAGE = REDIS_URL

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
# OAuth handled client-side with Supabase JS. Backend verifies JWT via middleware.

# Note: Logout is handled client-side via Supabase JS (supabase.auth.signOut()).

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
    route_result = route_message(user_id, session_id, message)
    # Normalize to text + debug
    if isinstance(route_result, dict):
        bot_response_text = route_result.get('reply') or ''
        debug_payload = route_result.get('debug') or {}
    else:
        bot_response_text = str(route_result)
        debug_payload = {}

    # Save bot response
    bot_msg_id = save_message(
        user_id=user_id,
        session_id=session_id,
        role='bot',
        message=bot_response_text,
        message_type='fsm_response'
    )
    
    return jsonify({
        'user_message_id': user_msg_id,
        'bot_message_id': bot_msg_id,
        'reply': bot_response_text,
        'debug': (debug_payload if not IS_PROD else {})
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

@app.route('/sessions/<session_id>', methods=['DELETE'])
@require_auth
def delete_session(session_id: str):
    """Delete a chat session and its messages for the authenticated user"""
    user_id = get_current_user_id()
    success = repo_delete_session(user_id, session_id)
    if success:
        return ('', 204)
    return jsonify({"error": "Session not found or could not be deleted"}), 404

# ==================== BASIC ENDPOINTS ====================

@app.route('/')
def welcome():
    """Serve the welcome/landing page with sign-in."""
    return render_template(
        'welcome.html',
        supabase_url=os.getenv('SUPABASE_URL', ''),
        supabase_anon_key=os.getenv('SUPABASE_ANON_KEY', '')
    )

@app.route('/chat')
def chat():
    """Serve the main chat interface."""
    return render_template(
        'chat.html',
        supabase_url=os.getenv('SUPABASE_URL', ''),
        supabase_anon_key=os.getenv('SUPABASE_ANON_KEY', '')
    )

@app.route('/index')
def index():
    """Legacy route - redirect to welcome page."""
    return render_template(
        'welcome.html',
        supabase_url=os.getenv('SUPABASE_URL', ''),
        supabase_anon_key=os.getenv('SUPABASE_ANON_KEY', '')
    )

import time
HEALTH_TTL_SECONDS = int(os.getenv("HEALTH_TTL_SECONDS", "60"))
_HEALTH_LAST_TS = 0.0
_HEALTH_LAST_PAYLOAD = None
_HEALTH_LAST_STATUS = 503

@app.route("/healthz")
@limiter.exempt
def healthz():
    """Shallow health: does not hit Supabase; safe for frequent platform checks."""
    return jsonify({"status": "ok"}), 200

@app.route("/health")
@limiter.exempt
def health_check():
    """Deep health: includes Supabase connectivity with simple caching to limit calls."""
    global _HEALTH_LAST_TS, _HEALTH_LAST_PAYLOAD, _HEALTH_LAST_STATUS
    now = time.time()
    if _HEALTH_LAST_PAYLOAD and (now - _HEALTH_LAST_TS) < HEALTH_TTL_SECONDS:
        return jsonify(_HEALTH_LAST_PAYLOAD), _HEALTH_LAST_STATUS

    db_connected = test_connection()
    payload = {
        "status": "ok" if db_connected else "degraded",
        "database": "connected" if db_connected else "disconnected",
        "auth": "supabase"
    }
    status_code = 200 if db_connected else 503
    _HEALTH_LAST_TS = now
    _HEALTH_LAST_PAYLOAD = payload
    _HEALTH_LAST_STATUS = status_code
    return jsonify(payload), status_code

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

    # Relax CSP in development to allow inline config and CDNs
    if not IS_PROD:
        csp = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
            "img-src 'self' data: https://www.gstatic.com; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "connect-src 'self' https://*.supabase.co; "
            "frame-ancestors 'none';"
        )
    else:
        csp = (
            "default-src 'self'; "
            "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "script-src 'self' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
            "img-src 'self' data: https://www.gstatic.com; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net; "
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
