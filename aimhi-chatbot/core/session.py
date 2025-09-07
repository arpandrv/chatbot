import uuid
import time
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Session storage
_sessions: Dict[str, float] = {}  # {session_id: last_activity_timestamp}
_last_cleanup = time.time()
_ttl_seconds = 1800  # 30 minutes

def validate_session(session_id: str) -> bool:
    """Check if session exists and is still valid.
    
    Args:
        session_id: Session identifier to validate
        
    Returns:
        True if session is valid, False otherwise
    """
    # Periodic cleanup every 5 minutes
    global _last_cleanup
    if time.time() - _last_cleanup > 300:
        _cleanup()
    
    if session_id not in _sessions:
        return False
    
    # Check if session expired
    age = time.time() - _sessions[session_id]
    if age > _ttl_seconds:
        del _sessions[session_id]
        return False
    
    return True

def touch_session(session_id: str) -> None:
    """Update session's last activity time.
    
    Args:
        session_id: Session identifier to update
    """
    _sessions[session_id] = time.time()

def create_session() -> str:
    """Generate a new session ID and track it.
    
    Returns:
        New session identifier
    """
    session_id = str(uuid.uuid4())
    _sessions[session_id] = time.time()
    logger.info(f"Created new session: {session_id}")
    return session_id

def remove_session(session_id: str) -> None:
    """Remove a session.
    
    Args:
        session_id: Session identifier to remove
    """
    if session_id in _sessions:
        del _sessions[session_id]
        logger.debug(f"Removed session: {session_id}")

def _cleanup() -> None:
    """Remove expired sessions."""
    global _last_cleanup
    now = time.time()
    expired = [
        sid for sid, last_activity in _sessions.items()
        if now - last_activity > _ttl_seconds
    ]
    
    for sid in expired:
        del _sessions[sid]
    
    _last_cleanup = now
    
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired sessions")

def get_session_stats() -> Dict:
    """Get session statistics.
    
    Returns:
        Dictionary with session stats
    """
    return {
        'active_sessions': len(_sessions),
        'last_cleanup': _last_cleanup
    }