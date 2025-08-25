# --- Imports ---
# Standard library imports first
import os
import uuid
import logging
import sqlite3
from datetime import datetime

# Flask and extensions
from flask import Flask, jsonify, request, g, render_template
from flask_cors import CORS
# Use a try-except for optional dependencies to prevent app from crashing if not installed
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    FLASK_LIMITER_AVAILABLE = True
except ImportError:
    FLASK_LIMITER_AVAILABLE = False

try:
    from flask_wtf.csrf import CSRFProtect, generate_csrf, validate_csrf
    FLASK_WTF_AVAILABLE = True
except ImportError:
    FLASK_WTF_AVAILABLE = False
    logger.warning("Flask-WTF is not installed. Application is running without CSRF protection.")

# Load environment variables securely
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass # Fails gracefully if python-dotenv is not installed

# Local application imports
from core.router import route_message
from core.session import new_session_id, get_session
from database.repository_v2 import init_db, DATABASE_PATH

# --- Logging Configuration ---
# Set up logging before creating the app instance
# This ensures that logging is available from the start
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Database Initialization ---
# It's good practice to initialize the DB once on startup
try:
    init_db()
    logger.info("Database initialized or already exists.")
except Exception as e:
    logger.error(f"FATAL: Database could not be initialized: {e}", exc_info=True)
    # Depending on requirements, you might want to exit here if the DB is critical
    # For this app, we'll let it run but it will likely fail on /chat requests.

# --- Flask App Initialization & Configuration ---
app = Flask(__name__)

# Security: Enforce a secure secret key in production
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
SECRET_KEY = os.getenv('SECRET_KEY')
if FLASK_ENV == 'production' and (not SECRET_KEY or SECRET_KEY == 'dev-key-change-in-production'):
    logger.error("FATAL: SECRET_KEY is not set or is insecure for production.")
    raise ValueError("SECRET_KEY must be set to a secure, random value in production.")
app.secret_key = SECRET_KEY or 'dev-key-for-development-only'

# Configure CORS with secure settings
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Development frontend
    "http://127.0.0.1:3000",
    "http://localhost:5000",  # Flask development server
    "http://127.0.0.1:5000",
    # Add production domain when available
    # "https://yourdomain.com",
]

# Add additional origins for development mode
if FLASK_ENV == 'development':
    ALLOWED_ORIGINS.extend([
        "http://localhost:8080",
        "http://127.0.0.1:8080"
    ])

# Secure CORS setup
CORS(app, 
     resources={
         r"/api/*": {
             "origins": ALLOWED_ORIGINS,
             "methods": ["GET", "POST"],
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True,
             "max_age": 86400  # Cache preflight for 24 hours
         },
         r"/chat": {
             "origins": ALLOWED_ORIGINS,
             "methods": ["POST"],
             "allow_headers": ["Content-Type"],
             "supports_credentials": True
         }
     },
     vary_header=True
)

# CSRF Protection: Critical for preventing cross-site request forgery
CSRF_ENABLED = os.getenv('CSRF_ENABLED', 'true').lower() == 'true'
if FLASK_WTF_AVAILABLE and CSRF_ENABLED:
    csrf = CSRFProtect(app)
    
    # Configure CSRF
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
    app.config['WTF_CSRF_SSL_STRICT'] = FLASK_ENV == 'production'
    
    logger.info("CSRF protection enabled")
else:
    csrf = None
    if CSRF_ENABLED:
        logger.warning("CSRF protection requested but Flask-WTF not available")

# Rate Limiting: A crucial security feature against abuse
if FLASK_LIMITER_AVAILABLE:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://" # For simple, single-process deployments. Use Redis for multi-process.
    )
else:
    logger.warning("Flask-Limiter is not installed. Application is running without rate limiting.")
    # Create a dummy decorator so the app doesn't crash
    class DummyLimiter:
        def limit(self, _):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()


# --- Database Connection Management (Connection Pool) ---
import threading
from contextlib import contextmanager

# Simple connection pool globals
_db_pool = []
_pool_lock = threading.Lock()
MAX_CONNECTIONS = 10

def _create_db_connection():
    """Create a properly configured database connection."""
    conn = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    # Configure for better performance
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON") 
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

@contextmanager 
def get_db():
    """Get database connection from simple pool."""
    conn = None
    try:
        # Try to get from pool
        with _pool_lock:
            if _db_pool:
                conn = _db_pool.pop()
            else:
                conn = _create_db_connection()
        
        yield conn
        conn.commit()
        
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        # Return to pool if healthy
        if conn:
            try:
                conn.execute("SELECT 1")  # Health check
                with _pool_lock:
                    if len(_db_pool) < MAX_CONNECTIONS:
                        _db_pool.append(conn)
                    else:
                        conn.close()
            except:
                conn.close()

@app.teardown_appcontext
def close_db(e=None):
    # Connection pool handles cleanup automatically
    pass


# --- API Routes ---
@app.route('/')
def index():
    """Serves the main static HTML file for the chat interface."""
    # This is a simple passthrough. All logic is handled by the frontend JS and /chat API.
    return render_template('index.html')

@app.route("/health")
def health_check():
    """Simple health check with minimal overhead."""
    return jsonify({"status": "ok"}), 200

# Exempt health check from CSRF if protection is enabled
if csrf:
    csrf.exempt(health_check)

@app.route("/api/csrf-token", methods=['GET'])
def get_csrf_token():
    """Endpoint to get CSRF token for API clients."""
    if FLASK_WTF_AVAILABLE and CSRF_ENABLED:
        token = generate_csrf()
        return jsonify({"csrf_token": token}), 200
    else:
        return jsonify({"csrf_token": None, "csrf_required": False}), 200

@app.route("/chat", methods=['POST'])
@limiter.limit("30 per minute") # Apply a specific, stricter limit to this expensive endpoint
def chat():
    """
    Main endpoint for processing user messages.
    - Validates CSRF token (if enabled)
    - Validates input
    - Delegates to the core application logic
    - Formats the response
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json(silent=True) or {}
    
    # Manual CSRF validation for JSON requests (if enabled)
    if FLASK_WTF_AVAILABLE and CSRF_ENABLED and FLASK_ENV == 'production':
        csrf_token = data.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not csrf_token:
            return jsonify({"error": "CSRF token missing"}), 400
        try:
            validate_csrf(csrf_token)
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            return jsonify({"error": "Invalid CSRF token"}), 400

    message = data.get("message", "").strip()
    if not message or len(message) > 1000:
        return jsonify({"error": "Field 'message' must be a non-empty string under 1000 characters."}), 400

    session_id = data.get("session_id") or str(uuid.uuid4())

    try:
        # The single point of delegation to the core logic.
        result = route_message(session_id, message)

        # Normalize the result from the router into a standard format.
        if isinstance(result, tuple) and len(result) == 2:
            reply, debug_info = result
        else:
            reply = str(result)
            debug_info = {}

        # Get current FSM state for the response payload
        fsm_state = get_session(session_id)['fsm'].state

        response_payload = {
            "reply": reply,
            "session_id": session_id,
            "state": fsm_state,
        }
        
        # Include CSRF token in response for next request
        if FLASK_WTF_AVAILABLE and CSRF_ENABLED:
            response_payload['csrf_token'] = generate_csrf()
        
        # Only include debug info if not in production for security
        if FLASK_ENV != 'production':
            response_payload['debug'] = debug_info

        return jsonify(response_payload), 200

    # Specific SQLite error handling
    except sqlite3.Error as e:
        logger.error(f"Database error in /chat for session {session_id}: {e}")
        return jsonify({"error": "Database temporarily unavailable. Please try again."}), 503
    
    except Exception:
        # Log the full error for developers but don't expose it to the user.
        logger.exception(f"Unhandled error in /chat route for session {session_id}")
        return jsonify({"error": "An internal server error occurred."}), 500


# --- Application-Wide Error Handlers ---
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not Found"}), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    return jsonify({"error": "Method Not Allowed"}), 405

@app.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Caught unhandled 500 error: {error}", exc_info=True)
    return jsonify({"error": "Internal Server Error"}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(error=f"Rate limit exceeded: {e.description}"), 429


# --- Security Middleware ---
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses to mitigate common web vulnerabilities."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # More secure CSP policy
    csp = "default-src 'self'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'self' https://cdn.jsdelivr.net;"
    response.headers['Content-Security-Policy'] = csp
    return response


# --- Main Entry Point for Running the App ---
if __name__ == '__main__':
    # This block is ONLY for local development.
    # Production deployments should use a WSGI server like Gunicorn.
    port = int(os.getenv("PORT", 5000))
    # `debug=True` is insecure and should only be used for local development
    debug_mode = FLASK_ENV != 'production'
    
    logger.info(f"Starting Flask development server on http://0.0.0.0:{port} (Debug: {debug_mode})")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)