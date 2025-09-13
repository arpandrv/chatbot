"""
Simplified Supabase Repository Module
===================================
Converted from OOP class to simple functions.
Reduced try/except blocks to essential error handling only.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
from config.supabase_client import supabase_service

logger = logging.getLogger(__name__)

# ---------- Session Management ----------

def create_session(user_id: str, fsm_state: str = "welcome") -> Optional[str]:
    """Create a new chat session for a user"""
    result = supabase_service.table('sessions').insert({
        'user_id': user_id,
        'fsm_state': fsm_state,
        'status': 'active'
    }).execute()
    
    if result.data:
        session_id = str(result.data[0]['session_id'])
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    logger.error("Failed to create session")
    return None

def get_session(user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data if user owns it"""
    result = supabase_service.table('sessions').select('*').eq(
        'session_id', session_id
    ).eq('user_id', user_id).execute()
    
    return result.data[0] if result.data else None

def update_session_state(user_id: str, session_id: str, fsm_state: Optional[str] = None, 
                        status: Optional[str] = None, ended_at: Optional[datetime] = None) -> bool:
    """Update session FSM state and/or status"""
    updates = {'last_activity': datetime.utcnow().isoformat()}
    
    if fsm_state is not None:
        updates['fsm_state'] = fsm_state
    if status is not None:
        updates['status'] = status
    if ended_at is not None:
        updates['ended_at'] = ended_at.isoformat()
    
    result = supabase_service.table('sessions').update(updates).eq(
        'session_id', session_id
    ).eq('user_id', user_id).execute()
    
    success = len(result.data) > 0
    if success:
        logger.debug(f"Updated session {session_id} state to {fsm_state}")
    else:
        logger.warning(f"Session {session_id} not found for user {user_id}")
    
    return success

# ---------- Message Management ----------

def save_message(user_id: str, session_id: str, role: str, message: str,
                message_type: str = "text", meta: Optional[Dict[str, Any]] = None,
                fsm_step: Optional[str] = None, is_final_response: bool = False) -> Optional[int]:
    """Save a message to chat history with ownership verification"""
    # Verify user owns the session
    session = get_session(user_id, session_id)
    if not session:
        logger.error(f"Session {session_id} not found or not owned by user")
        return None
    
    # Insert message
    result = supabase_service.table('chat_history').insert({
        'session_id': session_id,
        'role': role,
        'message': message,
        'message_type': message_type,
        'meta': meta or {},
        'fsm_step': fsm_step,
        'is_final_response': is_final_response
    }).execute()
    
    if result.data:
        message_id = result.data[0]['id']
        logger.debug(f"Saved {role} message {message_id} for session {session_id}")
        return message_id
    
    logger.error("Failed to save message")
    return None

def get_chat_history(user_id: str, session_id: str, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
    """Get chat history for a user's session"""
    # Verify session ownership
    session = get_session(user_id, session_id)
    if not session:
        logger.error(f"Session {session_id} not found or not owned by user")
        return None
    
    result = supabase_service.table('chat_history').select(
        'id, role, message, message_type, meta, ts, fsm_step, is_final_response'
    ).eq('session_id', session_id).order('ts', desc=False).limit(limit).execute()
    
    return result.data or []

def accept_response(user_id: str, session_id: str, step: str, message_id: int) -> bool:
    """Mark a specific response as the final response for a step"""
    # Verify message ownership
    message_result = supabase_service.table('chat_history').select(
        'id, session_id, fsm_step'
    ).eq('id', message_id).execute()
    
    if not message_result.data:
        logger.error("Message not found")
        return False
    
    message = message_result.data[0]
    if message['session_id'] != session_id or message['fsm_step'] != step:
        logger.error("Message doesn't match session/step")
        return False
    
    # Verify session ownership
    session = get_session(user_id, session_id)
    if not session:
        logger.error("Session not owned by user")
        return False
    
    # Unmark all previous final responses for this step
    supabase_service.table('chat_history').update({
        'is_final_response': False
    }).eq('session_id', session_id).eq('fsm_step', step).execute()
    
    # Mark the target message as final
    result = supabase_service.table('chat_history').update({
        'is_final_response': True
    }).eq('id', message_id).execute()
    
    if result.data:
        logger.info(f"Accepted response {message_id} for step {step} in session {session_id}")
        return True
    
    logger.error("Failed to accept response")
    return False

def get_final_responses_map(user_id: str, session_id: str) -> Dict[str, Any]:
    """Get map of final responses by FSM step"""
    # Verify session ownership
    session = get_session(user_id, session_id)
    if not session:
        logger.error("Session not owned by user")
        return {}
    
    result = supabase_service.table('chat_history').select(
        'fsm_step, message'
    ).eq('session_id', session_id).eq('is_final_response', True).execute()
    
    # Convert to dict
    responses_map = {}
    for row in result.data or []:
        if row['fsm_step']:
            responses_map[row['fsm_step']] = row['message']
    
    return responses_map

# ---------- Analytics and Logging ----------

def record_risk_detection(user_id: str, session_id: str, message_id: Optional[int],
                         label: str, confidence: Optional[float] = None,
                         method: Optional[str] = None, model: Optional[str] = None,
                         details: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """Record a risk detection event"""
    # Verify session ownership
    session = get_session(user_id, session_id)
    if not session:
        logger.error("Session not owned by user")
        return None
    
    result = supabase_service.table('risk_detections').insert({
        'session_id': session_id,
        'message_id': message_id,
        'label': label,
        'confidence': confidence,
        'method': method,
        'model': model,
        'details': details or {}
    }).execute()
    
    return result.data[0]['id'] if result.data else None

def record_intent_classification(user_id: str, session_id: str, message_id: Optional[int],
                                label: str, confidence: Optional[float] = None,
                                method: Optional[str] = None) -> Optional[int]:
    """Record an intent classification result"""
    # Verify session ownership
    session = get_session(user_id, session_id)
    if not session:
        logger.error("Session not owned by user")
        return None
    
    result = supabase_service.table('intent_classifications').insert({
        'session_id': session_id,
        'message_id': message_id,
        'label': label,
        'confidence': confidence,
        'method': method
    }).execute()
    
    return result.data[0]['id'] if result.data else None

# ---------- Utility Functions ----------

def get_user_sessions(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get all sessions for a user"""
    result = supabase_service.table('sessions').select('*').eq(
        'user_id', user_id
    ).order('last_activity', desc=True).limit(limit).execute()
    
    return result.data or []

def delete_old_sessions(days_old: int = 7) -> int:
    """Delete old inactive sessions (admin function)"""
    cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
    
    result = supabase_service.table('sessions').delete().lt(
        'last_activity', cutoff_date.isoformat()
    ).execute()
    
    deleted_count = len(result.data) if result.data else 0
    logger.info(f"Deleted {deleted_count} old sessions")
    return deleted_count

# ---------- Legacy Compatibility Functions ----------

def insert_message(user_id: str, session_id: str, role: str, message: Optional[str],
                  message_type: str = "text", meta: Optional[Dict[str, Any]] = None,
                  fsm_step: Optional[str] = None, is_final_response: bool = False) -> Optional[int]:
    """Alias for save_message to maintain compatibility"""
    return save_message(user_id, session_id, role, message, message_type, meta, fsm_step, is_final_response)

def get_messages(user_id: str, session_id: str, limit: int = 200) -> Optional[List[Dict[str, Any]]]:
    """Alias for get_chat_history to maintain compatibility"""
    return get_chat_history(user_id, session_id, limit)

def record_intent(user_id: str, session_id: str, message_id: Optional[int],
                 label: str, confidence: Optional[float] = None,
                 method: Optional[str] = None) -> Optional[int]:
    """Alias for record_intent_classification to maintain compatibility"""
    return record_intent_classification(user_id, session_id, message_id, label, confidence, method)