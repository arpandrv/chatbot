# --- Standard Library Imports ---
import os
import uuid
import logging
# TODO: Supabase Migration - SQLite import removed
# import sqlite3
import atexit

# --- Flask and Extensions (Required) ---
from flask import Flask, jsonify, request, render_template, abort, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf, validate_csrf

# --- Database Connection Management ---
# TODO: Supabase client will replace SQLite connection pooling
# from contextlib import contextmanager
# from queue import LifoQueue, Empty

# --- Load Environment Variables ---
from dotenv import load_dotenv

# Local application imports
from core.router import route_message, get_current_state
from core.session import touch_session

# TODO: Replace with Supabase imports after migration
# from config.supabase import supabase
# REMOVED: from database.repository_v2 import init_db, DATABASE_PATH

load_dotenv()

FLASK_ENV = os.getenv("FLASK_ENV", "production")
IS_PROD   = (FLASK_ENV == "production")
SECRET_KEY = os.getenv("SECRET_KEY")
CSRF_ENABLED = os.getenv("CSRF_ENABLED", "true").lower() == "true"
# TODO: Remove SQLite-specific configuration after Supabase migration
# POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
# POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "5"))  # seconds to wait for a free connection
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
origins_env = os.getenv("CORS_ORIGINS", "").strip()

# --- Logging Configuration ---
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app")


# --- Flask App Initialization & Configuration ---
app = Flask(__name__)

# --- Secret Key Configuration ---
if IS_PROD:
    if not SECRET_KEY or SECRET_KEY == 'dev-key-change-in-production':
        logger.critical("❌ FATAL: SECRET_KEY is not set or is insecure for production.")
        raise SystemExit("SECRET_KEY must be set to a secure, random value in production.")
    app.secret_key = SECRET_KEY
else:
    app.secret_key = SECRET_KEY or 'dev-key-for-development-only'



# --- CORS ---
# In production, set: CORS_ORIGINS="https://yourdomain.com,https://admin.yourdomain.com"
if IS_PROD:
    ORIGINS = []
    for o in origins_env.split(","):
        o = o.strip()
        if o:
            ORIGINS.append(o)
    if not ORIGINS:
        raise SystemExit("CORS_ORIGINS must be set in production (comma-separated).")
else:
    ORIGINS = [r"http://localhost:\d+", r"http://127\.0\.0\.1:\d+"]


cors_common = {
    "origins": ORIGINS,
    "supports_credentials": True,
    "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token"],
    "methods": ["GET", "POST"],
    "max_age": 86400,
}

CORS(
    app,
    resources={
        r"/api/.*": cors_common,
        r"/chat": {**cors_common, "methods": ["POST"]},
        r"/health": cors_common,
        r"/": cors_common
    },
    vary_header=True,
)

# --- CSRF Protection ---
app.config.update(
    WTF_CSRF_TIME_LIMIT=3600,
    WTF_CSRF_SSL_STRICT=IS_PROD,
    WTF_CSRF_CHECK_DEFAULT=False, # we manually validate JSON endpoints

     # session cookie hardening
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PROD,
)
csrf = CSRFProtect(app) if CSRF_ENABLED else None
logger.info("CSRF protection %s", "enabled" if CSRF_ENABLED else "disabled by config")

# Rate Limiting: A crucial security feature against abuse
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://" # In-memory for simplicity, needs to use redis in production
)




# TODO: Supabase Migration - Connection pool logic removed
# All database operations will use Supabase client instead of SQLite connection pooling
# 
# REMOVED: ~90 lines of complex SQLite connection pool management including:
# - LifoQueue connection pool (_pool)
# - Connection creation and management functions
# - Transaction management with BEGIN/COMMIT/ROLLBACK
# - Connection pooling optimization and cleanup
# - Process exit handlers for connection cleanup
#
# REPLACEMENT: Simple Supabase client initialization (to be implemented):
# from config.supabase import supabase
#
# Benefits after migration:
# - No connection management needed (handled by Supabase)
# - No transaction complexity (atomic operations built-in)
# - No connection leaks or cleanup needed
# - Automatic scaling and connection pooling




# --- Database Initialization ---
# TODO: Supabase Migration - Replace SQLite initialization
logger.info("✅ Database initialization skipped during migration.")

# TODO: Uncomment after Supabase migration is complete:
# try:
#     from config.supabase import supabase
#     supabase.table('sessions').select('count').limit(1).execute()
#     logger.info("✅ Supabase connection verified successfully.")
# except Exception as e:
#     logger.critical("❌ FATAL: Supabase connection failed", exc_info=True)
#     if IS_PROD:
#         raise SystemExit("Startup aborted: Database could not be initialized.")
#     else:
#         raise



# chunk4-start


# --- API Routes ---
@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')

@app.route("/health")
def health_check():
    # TODO: Supabase Migration - Add database connectivity check
    # try:
    #     from config.supabase import supabase
    #     # Simple connectivity test
    #     response = supabase.table('sessions').select('count').limit(1).execute()
    #     return jsonify({"status": "ok", "database": "connected"}), 200
    # except Exception as e:
    #     logger.error(f"Database health check failed: {e}")
    #     return jsonify({"status": "error", "database": "disconnected"}), 503
    
    return jsonify({"status": "ok"}), 200

# CSRF exemptions for views that do not need automatic form-based CSRF
if csrf:
    csrf.exempt(health_check)

@app.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    if CSRF_ENABLED:
        return jsonify({"csrf_token": generate_csrf(), "csrf_required": True}), 200
    return jsonify({"csrf_token": None, "csrf_required": False}), 200


def _require_json() -> dict:
    """Ensure JSON request and return parsed body, or abort with 4xx."""
    if not request.is_json:
        abort(make_response(jsonify(error="Content-Type must be application/json"), 415))
    data = request.get_json(silent=True)
    if data is None:
        abort(make_response(jsonify(error="Malformed JSON body"), 400))
    return data


def _validate_json_csrf_or_400(data: dict) -> None:
    """Manual CSRF for JSON (prod only), aborts on failure."""
    if not (CSRF_ENABLED and IS_PROD):
        return
    token = data.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not token:
        abort(make_response(jsonify(error="CSRF token missing"), 400))
    try:
        validate_csrf(token)
    except Exception as e:
        logger.warning("CSRF validation failed: %s", e)
        abort(make_response(jsonify(error="Invalid CSRF token"), 400))


@app.route("/chat", methods=["POST"])
@limiter.limit("30 per minute")  # stricter rate for this endpoint
def chat():
    data = _require_json()
    _validate_json_csrf_or_400(data)

    message = (data.get("message") or "").strip()
    if not message or len(message) > 1000:
        return jsonify({"error": "Field 'message' must be a non-empty string under 1000 characters."}), 400

    session_id = data.get("session_id") or str(uuid.uuid4())

    try:
        result = route_message(session_id, message)
        reply, debug_info = (result if isinstance(result, tuple) and len(result) == 2 else (str(result), {}))

        # Get current FSM state from router
        fsm_state = get_current_state(session_id)

        payload = {
            "reply": reply,
            "session_id": session_id,
            "state": fsm_state,
        }
        if CSRF_ENABLED:
            payload["csrf_token"] = generate_csrf()
        if not IS_PROD:
            payload["debug"] = debug_info

        return jsonify(payload), 200

    # TODO: Supabase Migration - Update error handling for Supabase exceptions
    # except sqlite3.Error as e:
    #     logger.error("Database error in /chat for session %s: %s", session_id, e)
    #     return jsonify({"error": "Database temporarily unavailable. Please try again."}), 503
    
    # TODO: Replace with Supabase error handling:
    # from postgrest.exceptions import APIError
    # except APIError as e:
    #     logger.error("Supabase error in /chat for session %s: %s", session_id, e)
    #     return jsonify({"error": "Database temporarily unavailable. Please try again."}), 503

    except Exception:
        logger.exception("Unhandled error in /chat for session %s", session_id)
        return jsonify({"error": "An internal server error occurred."}), 500

# keep your existing exemption since we do manual JSON CSRF:
if csrf:
    csrf.exempt(chat)


#chunk4-end




#chunk5-start

# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(_):
    return jsonify({"error": "Not Found"}), 404

@app.errorhandler(405)
def method_not_allowed_error(_):
    return jsonify({"error": "Method Not Allowed"}), 405

@app.errorhandler(500)
def internal_server_error(e):
    logger.error("Caught unhandled 500: %s", e, exc_info=True)
    return jsonify({"error": "Internal Server Error"}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(error=f"Rate limit exceeded: {e.description}"), 429

# --- Security Headers ---
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    # X-XSS-Protection is legacy; keep for old browsers, harmless for modern
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # CSP: adjust if you load scripts/styles from other CDNs
    csp = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response


#chunk5-end


# --- Main (dev only) ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = (not IS_PROD)
    logger.info("Starting Flask server on http://0.0.0.0:%d (Debug: %s)", port, debug_mode)
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
