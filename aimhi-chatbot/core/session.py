# chatbot/aimhi-chatbot/core/session.py

import uuid
import logging
import time
from typing import Dict
from core.fsm import ChatBotFSM

logger = logging.getLogger(__name__)

# Database integration
from database.repository_v2 import get_session_data, create_session, update_session_state

# Simple session storage with periodic cleanup
class SimpleSessionStore:
    def __init__(self):
        self.sessions = {}
        self.last_cleanup = time.time()
    
    def get_session(self, session_id: str):
        """Get or create session with periodic cleanup."""
        # Cleanup every 10 minutes
        if time.time() - self.last_cleanup > 600:
            self._cleanup()
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'fsm': None,
                'created': time.time()
            }
        
        return self.sessions[session_id]
    
    def _cleanup(self):
        """Remove sessions older than 30 minutes."""
        cutoff = time.time() - 1800  # 30 minutes
        expired = [
            sid for sid, data in self.sessions.items()
            if data['created'] < cutoff
        ]
        
        for sid in expired:
            del self.sessions[sid]
        
        self.last_cleanup = time.time()
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

# Global session store
_session_store = SimpleSessionStore()

def get_session(session_id: str) -> dict:
    """Get or create a user session."""
    session_data = _session_store.get_session(session_id)
    
    # Create FSM if not already created
    if session_data['fsm'] is None:
        # Check database for existing session state
        db_session = get_session_data(session_id)
        
        if db_session:
            # Session exists in DB - create FSM at the stored state
            current_state = db_session.get('fsm_state', 'welcome')
            fsm = ChatBotFSM(session_id, initial_state=current_state)
            logger.info(f"Loaded existing session {session_id} at state: {current_state}")
        else:
            # New session - start from welcome
            fsm = ChatBotFSM(session_id, initial_state='welcome')
            create_session(session_id, fsm_state='welcome')
            logger.info(f"Created new session {session_id}")
        
        session_data['fsm'] = fsm
        session_data['session_id'] = session_id
    
    return session_data

def new_session_id() -> str:
    """Generate a new unique session identifier"""
    return str(uuid.uuid4())

def clear_session(session_id: str):
    """Remove a session from memory (but not from database)"""
    if session_id in _session_store.sessions:
        del _session_store.sessions[session_id]
        logger.debug(f"Cleared session {session_id} from memory")

def get_session_stats() -> dict:
    """Get statistics about active sessions"""
    return {
        'active_sessions': len(_session_store.sessions),
        'last_cleanup': _session_store.last_cleanup
    }