# --- Standard Library Imports ---
import os
import uuid
import logging
import sqlite3
import atexit

# --- Flask and Extensions (Required) ---
from flask import Flask, jsonify, request, render_template, abort, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf, validate_csrf

# --- Database Connection Management (Connection Pool) ---
from contextlib import contextmanager
from queue import LifoQueue, Empty

# --- Load Environment Variables ---
from dotenv import load_dotenv

# Local application imports
from core.router import route_message
from core.session import get_session
from database.repository_v2 import init_db, DATABASE_PATH

load_dotenv()

FLASK_ENV = os.getenv("FLASK_ENV", "production")
IS_PROD   = (FLASK_ENV == "production")
SECRET_KEY = os.getenv("SECRET_KEY")
CSRF_ENABLED = os.getenv("CSRF_ENABLED", "true").lower() == "true"
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "5"))  # seconds to wait for a free connection
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




# --- DB Connection Pool (SQLite + LIFO queue) ---
_pool: LifoQueue[sqlite3.Connection] = LifoQueue(maxsize=POOL_SIZE)

def _create_db_connection() -> sqlite3.Connection:
    """
    Create a configured SQLite connection.

    Note: isolation_level=None => autocommit is ON by default; we start
    transactions explicitly with BEGIN and finish with COMMIT/ROLLBACK.
    """
    conn = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30,
        check_same_thread=False,
        isolation_level=None,  # explicit transaction control
    )
    conn.row_factory = sqlite3.Row
    # Pragmas (applied per-connection)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA strict = ON")
    return conn

def _get_conn() -> sqlite3.Connection:
    """Get a connection from pool or create a new one."""
    try:
        return _pool.get(block=False)
    except Empty:
        return _create_db_connection()

def _return_conn(conn: sqlite3.Connection) -> None:
    """Return connection to pool; if full or broken, close."""
    if conn is None:
        return
    try:
        _pool.put(conn, block=False)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass

@contextmanager
def get_db():
    """
    Usage:
        with get_db() as conn:
            cur = conn.execute("SELECT 1")
            ...
    Manages BEGIN/COMMIT/ROLLBACK and returns pooled connections.
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        yield conn
        conn.execute("COMMIT")
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            logger.exception("Failed to ROLLBACK after error")
        logger.exception("DB error: %s", e)
        raise
    finally:
        _return_conn(conn)

# Optional: pre-warm a couple of connections
try:
    for _ in range(min(POOL_SIZE, 2)):
        _return_conn(_create_db_connection())
except Exception:
    logger.warning("Failed to pre-warm DB pool", exc_info=True)

def _close_pool():
    """Close any pooled connections at process exit."""
    drained = 0
    while True:
        try:
            conn = _pool.get(block=False)
        except Empty:
            break
        try:
            conn.close()
            drained += 1
        except Exception:
            pass
    logger.info("Database pool closed (drained %d conns)", drained)

atexit.register(_close_pool)




# --- Database Initialization (Required) ---
try:
    init_db()
    logger.info("✅ Database initialized successfully.")
except Exception as e:
    logger.critical("❌ FATAL: Database initialization failed", exc_info=True)

    if IS_PROD:
        raise SystemExit("Startup aborted: Database could not be initialized.")
    else:
        raise  # Shows full traceback in dev for debugging



# chunk4-start


# --- API Routes ---
@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')

@app.route("/health")
def health_check():
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

        fsm_state = get_session(session_id)["fsm"].state

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

    except sqlite3.Error as e:
        logger.error("Database error in /chat for session %s: %s", session_id, e)
        return jsonify({"error": "Database temporarily unavailable. Please try again."}), 503

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
