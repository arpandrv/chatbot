# Tests for config/auth_middleware
#
# Strategy:
# - Create a tiny Flask app with routes protected by @require_auth and @optional_auth.
# - Patch jwt.decode to simulate: valid token (returns dict with 'sub'), ExpiredSignatureError, InvalidTokenError, and generic Exception.
# - Patch env SUPABASE_JWT_SECRET (via config.supabase_client.JWT_SECRET) to ensure middleware has a secret.
#
# Test cases:
# - No Authorization header on @require_auth route -> 401 with helpful message.
# - Malformed Authorization header (e.g., 'Token abc') -> 401 invalid format.
# - ExpiredSignatureError -> 401 'Token has expired'.
# - InvalidTokenError -> 401 'Invalid token'.
# - Valid token -> 200 and request.user_id set and accessible in route.
# - @optional_auth without header -> 200 and request.user_id is None; with invalid token -> 401 invalid authentication.
#
# Notes:
# - Use Flask's test_client to call routes; avoid real JWT verification.
# - Ensure exceptions are raised via side_effect on patched jwt.decode.

