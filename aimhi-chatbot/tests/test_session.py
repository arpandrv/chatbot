# Tests for core/session.py (in-memory session manager)
#
# Use unittest.TestCase; no external deps required. Patch time.time to simulate TTL expiry and cleanup cadence.
#
# Test cases:
# - create_session returns a UUID string and is tracked in internal storage.
# - validate_session returns True for active session, False for unknown, and False for expired sessions.
# - touch_session updates last activity; verify by simulating time progression and validating before/after touch.
# - remove_session deletes the session and validate_session becomes False.
# - _cleanup runs every ~5 minutes: simulate time advancement to trigger cleanup and verify expired sessions removed.
# - get_session_stats returns counts and last_cleanup timestamp; ensure values change after cleanup.
#
# Notes:
# - Patch time.time using unittest.mock to control timestamps deterministically.
# - Do not rely on module globals across tests; consider reloading module or resetting internal dicts between tests.

