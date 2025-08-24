# chatbot/aimhi-chatbot/core/session.py

import uuid
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from core.fsm import ChatBotFSM

logger = logging.getLogger(__name__)

# Database integration
try:
    from database.repository_v2 import get_session_data, create_session, update_session_state
    DB_AVAILABLE = True
except ImportError:
    logger.warning("Database repository not found. Sessions will be in-memory only.")
    DB_AVAILABLE = False
    def get_session_data(session_id): return None
    def create_session(session_id, fsm_state): pass
    def update_session_state(session_id, state): pass

# In-memory cache with TTL
class SessionCache:
    def __init__(self, ttl_minutes: int = 30):
        self._sessions: Dict[str, Dict] = {}
        self._last_access: Dict[str, datetime] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, session_id: str) -> Optional[Dict]:
        """Get session from cache if not expired"""
        if session_id in self._sessions:
            last_access = self._last_access.get(session_id)
            if last_access and (datetime.now() - last_access) < self.ttl:
                self._last_access[session_id] = datetime.now()
                return self._sessions[session_id]
            else:
                # Expired, remove from cache
                self.remove(session_id)
        return None
    
    def set(self, session_id: str, session_data: Dict):
        """Store session in cache"""
        self._sessions[session_id] = session_data
        self._last_access[session_id] = datetime.now()
        
        # Clean up old sessions if cache is getting large
        if len(self._sessions) > 1000:
            self._cleanup_expired()
    
    def remove(self, session_id: str):
        """Remove session from cache"""
        self._sessions.pop(session_id, None)
        self._last_access.pop(session_id, None)
    
    def _cleanup_expired(self):
        """Remove expired sessions from cache"""
        now = datetime.now()
        expired = [
            sid for sid, last_access in self._last_access.items()
            if (now - last_access) >= self.ttl
        ]
        for sid in expired:
            self.remove(sid)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions from cache")

# Global cache instance
_session_cache = SessionCache(ttl_minutes=30)

def get_session(session_id: str) -> dict:
    """
    Get or create a user session.
    Sessions progress forward only - no state restoration.
    """
    # Check cache first
    cached_session = _session_cache.get(session_id)
    if cached_session:
        return cached_session
    
    # Not in cache, check database
    if DB_AVAILABLE:
        session_data = get_session_data(session_id)
        
        if session_data:
            # Session exists in DB - create FSM at the stored state
            current_state = session_data.get('fsm_state', 'welcome')
            
            # Create FSM starting from the current state (not resetting to welcome)
            fsm = ChatBotFSM(session_id, initial_state=current_state)
            
            # Note: We're NOT trying to restore responses or attempts
            # The FSM starts fresh at its current state
            
            logger.info(f"Loaded existing session {session_id} at state: {current_state}")
        else:
            # New session - start from welcome
            fsm = ChatBotFSM(session_id, initial_state='welcome')
            create_session(session_id, fsm_state='welcome')
            logger.info(f"Created new session {session_id}")
    else:
        # No database, create in-memory only
        fsm = ChatBotFSM(session_id, initial_state='welcome')
        logger.debug(f"Created in-memory session {session_id}")
    
    # Store in cache
    session = {'fsm': fsm, 'session_id': session_id}
    _session_cache.set(session_id, session)
    
    return session

def new_session_id() -> str:
    """Generate a new unique session identifier"""
    return str(uuid.uuid4())

def clear_session(session_id: str):
    """Remove a session from cache (but not from database)"""
    _session_cache.remove(session_id)
    logger.debug(f"Cleared session {session_id} from cache")

def get_cache_stats() -> dict:
    """Get statistics about the session cache"""
    return {
        'cached_sessions': len(_session_cache._sessions),
        'cache_ttl_minutes': _session_cache.ttl.total_seconds() / 60
    }