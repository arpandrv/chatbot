"""
Simplified User-Scoped Message Router
====================================
Reduced try/except blocks and converted FSM class to simple functions.
"""

import json
import logging
import time
import os
from typing import Dict, List, Optional, Any

# --- Core Application Imports ---
from database.repository import (
    get_session, update_session_state, record_risk_detection,
    record_intent_classification
)


# --- NLP Components ---
import sys
sys.path.append('../')

try:
    from nlp.risk_detector import contains_risk, get_crisis_resources
    from nlp.intent_roberta_zeroshot import classify_intent
    from nlp.preprocessor import normalize_text
    from nlp.response_selector import VariedResponseSelector
    from nlp.sentiment import analyze_sentiment
except ImportError as e:
    logging.error(f"Failed to import NLP components: {e}")
    # Fallback implementations
    def contains_risk(text): return False
    def get_crisis_resources(): return "Crisis resources would be shown here."
    def classify_intent(text, current_step=None): return {'label': 'unclear', 'confidence': 0.0}
    def normalize_text(text): return text.strip()
    def analyze_sentiment(text): return {'label': 'neutral'}
    
    class VariedResponseSelector:
        def get_response(self, *args, **kwargs): return "Response not available"
        def get_prompt(self, *args, **kwargs): return "Prompt not available"

# --- Configuration ---
logger = logging.getLogger(__name__)
response_selector = VariedResponseSelector()
LLM_ENABLED = os.getenv('LLM_ENABLED', 'false').lower() == 'true'

# --- FSM Functions (converted from class) ---
FSM_STATES = ['welcome', 'support_people', 'strengths', 'worries', 'goals', 'llm_conversation']
FSM_TRANSITIONS = {
    'welcome': 'support_people',
    'support_people': 'strengths', 
    'strengths': 'worries',
    'worries': 'goals',
    'goals': 'llm_conversation'
}

# In-memory FSM cache
_fsm_cache = {}  # {f"{user_id}:{session_id}": {'state': str, 'attempts': int}}

def get_fsm_key(user_id: str, session_id: str) -> str:
    """Create a unique key for FSM cache"""
    return f"{user_id}:{session_id}"

def get_fsm_state(user_id: str, session_id: str) -> str:
    """Get current FSM state for user session"""
    fsm_key = get_fsm_key(user_id, session_id)
    
    if fsm_key not in _fsm_cache:
        # Try to restore state from database
        session = get_session(user_id, session_id)
        if session and session.get('fsm_state'):
            state = session['fsm_state']
            logger.info(f"Restored FSM state for {session_id}: {state}")
        else:
            state = 'welcome'
            logger.info(f"Created new FSM for session {session_id}")
        
        _fsm_cache[fsm_key] = {'state': state, 'attempts': 0}
    
    return _fsm_cache[fsm_key]['state']

def set_fsm_state(user_id: str, session_id: str, new_state: str):
    """Set FSM state for user session"""
    fsm_key = get_fsm_key(user_id, session_id)
    _fsm_cache[fsm_key] = {'state': new_state, 'attempts': 0}

def get_fsm_attempts(user_id: str, session_id: str) -> int:
    """Get attempt count for current state"""
    fsm_key = get_fsm_key(user_id, session_id)
    return _fsm_cache.get(fsm_key, {}).get('attempts', 0)

def increment_fsm_attempts(user_id: str, session_id: str):
    """Increment attempt count"""
    fsm_key = get_fsm_key(user_id, session_id)
    if fsm_key in _fsm_cache:
        _fsm_cache[fsm_key]['attempts'] += 1

def reset_fsm_attempts(user_id: str, session_id: str):
    """Reset attempt count"""
    fsm_key = get_fsm_key(user_id, session_id)
    if fsm_key in _fsm_cache:
        _fsm_cache[fsm_key]['attempts'] = 0

def can_advance_fsm(current_state: str) -> bool:
    """Check if FSM can advance from current state"""
    return current_state in FSM_TRANSITIONS

def advance_fsm_state(user_id: str, session_id: str) -> bool:
    """Advance FSM to next state"""
    current_state = get_fsm_state(user_id, session_id)
    
    if can_advance_fsm(current_state):
        new_state = FSM_TRANSITIONS[current_state]
        set_fsm_state(user_id, session_id, new_state)
        return True
    
    return False

def should_force_advance(user_id: str, session_id: str, max_attempts: int = 2) -> bool:
    """Check if should force advance after max attempts"""
    return get_fsm_attempts(user_id, session_id) >= max_attempts

# --- Main Router Function ---
def route_message(user_id: str, session_id: str, message: str) -> str:
    """Main routing function for user-scoped message processing"""
    start_time = time.time()
    
    # Normalize message
    normalized_message = normalize_text(message)
    logger.debug(f"Processing message for user {user_id}, session {session_id}")
    
    # Universal risk detection (highest priority)
    if contains_risk(normalized_message):
        logger.warning(f"Risk detected in session {session_id} for user {user_id}")
        reply = get_crisis_resources()
        
        # Record risk detection
        record_risk_detection(
            user_id=user_id,
            session_id=session_id,
            message_id=None,
            label='risk',
            method='rule_based'
        )
        
        return reply
    
    # Get current FSM state
    current_state = get_fsm_state(user_id, session_id)
    
    # Handle different conversation types
    if current_state == 'llm_conversation':
        reply = handle_llm_conversation(user_id, session_id, message)
    else:
        reply = handle_fsm_conversation(user_id, session_id, message, current_state)
    
    # Update session state if changed
    new_state = get_fsm_state(user_id, session_id)
    if new_state != current_state:
        update_session_state(user_id, session_id, fsm_state=new_state)
        logger.debug(f"Session {session_id} advanced: {current_state} -> {new_state}")
    
    processing_time = int((time.time() - start_time) * 1000)
    logger.debug(f"Message processed in {processing_time}ms")
    
    return reply

# --- Conversation Handlers ---
def handle_fsm_conversation(user_id: str, session_id: str, message: str, current_state: str) -> str:
    """Handle structured FSM-driven conversation"""
    
    # Run NLP analysis
    intent_result = classify_intent(message, current_step=current_state)
    sentiment_result = analyze_sentiment(message)
    
    # Record intent classification
    record_intent_classification(
        user_id=user_id,
        session_id=session_id,
        message_id=None,
        label=intent_result.get('label', 'unclear'),
        confidence=intent_result.get('confidence'),
        method=intent_result.get('method', 'roberta_zeroshot')
    )
    
    # Route to appropriate state handler
    state_handlers = {
        'welcome': handle_welcome_state,
        'support_people': handle_support_people_state,
        'strengths': handle_strengths_state,
        'worries': handle_worries_state,
        'goals': handle_goals_state,
    }
    
    handler = state_handlers.get(current_state, handle_fallback_state)
    return handler(user_id, session_id, message, intent_result, sentiment_result)

def handle_llm_conversation(user_id: str, session_id: str, message: str) -> str:
    """Handle free-form LLM-driven conversation"""
    if not LLM_ENABLED:
        return "I'm not able to continue our conversation right now. Please try again later."
    
    # TODO: Implement LLM conversation logic
    logger.info(f"LLM conversation for user {user_id}, session {session_id}")
    return "LLM conversation mode - this would be implemented with your existing LLM system."

# --- Individual FSM State Handlers ---
def handle_welcome_state(user_id: str, session_id: str, message: str, intent_result: dict, sentiment_result: dict) -> str:
    """Handle the welcome state"""
    user_sentiment = sentiment_result.get('label', 'neutral')
    
    if len(message.strip()) > 3:  # Any substantial response moves forward
        if advance_fsm_state(user_id, session_id):
            return response_selector.get_response('welcome', 'ready_response', session_id, user_sentiment)
        else:
            logger.error(f"Cannot advance from welcome state for session {session_id}")
            return response_selector.get_response('welcome', 'greeting', session_id, user_sentiment)
    else:
        return response_selector.get_response('welcome', 'greeting', session_id, user_sentiment)

def handle_support_people_state(user_id: str, session_id: str, message: str, intent_result: dict, sentiment_result: dict) -> str:
    """Handle the support_people state with progressive fallback"""
    intent = intent_result.get('label', 'unclear')
    user_sentiment = sentiment_result.get('label', 'neutral')
    
    if intent != 'unclear':
        # Clear response - save and advance
        reset_fsm_attempts(user_id, session_id)
        
        if advance_fsm_state(user_id, session_id):
            ack = response_selector.get_response('support_people', 'acknowledgment', session_id, user_sentiment)
            prompt = response_selector.get_prompt('strengths', session_id=session_id)
            return f"{ack} {prompt}"
        else:
            return response_selector.get_response('support_people', 'acknowledgment', session_id, user_sentiment)
    else:
        # Unclear response - use progressive fallback
        increment_fsm_attempts(user_id, session_id)
        
        if should_force_advance(user_id, session_id):
            # After max attempts, move forward anyway
            reset_fsm_attempts(user_id, session_id)
            
            if advance_fsm_state(user_id, session_id):
                trans = response_selector.get_response('support_people', 'transition_unclear', session_id)
                prompt = response_selector.get_prompt('strengths', session_id=session_id)
                return f"{trans} {prompt}"
            else:
                return response_selector.get_response('support_people', 'transition_unclear', session_id)
        else:
            # First attempt - ask for clarification
            return response_selector.get_response('support_people', 'clarify', session_id)

def handle_strengths_state(user_id: str, session_id: str, message: str, intent_result: dict, sentiment_result: dict) -> str:
    """Handle the strengths state with progressive fallback"""
    intent = intent_result.get('label', 'unclear')
    user_sentiment = sentiment_result.get('label', 'neutral')
    
    if intent != 'unclear':
        reset_fsm_attempts(user_id, session_id)
        
        if advance_fsm_state(user_id, session_id):
            ack = response_selector.get_response('strengths', 'acknowledgment', session_id, user_sentiment)
            prompt = response_selector.get_prompt('worries', session_id=session_id)
            return f"{ack} {prompt}"
        else:
            return response_selector.get_response('strengths', 'acknowledgment', session_id, user_sentiment)
    else:
        increment_fsm_attempts(user_id, session_id)
        
        if should_force_advance(user_id, session_id):
            reset_fsm_attempts(user_id, session_id)
            
            if advance_fsm_state(user_id, session_id):
                trans = response_selector.get_response('strengths', 'transition_advance', session_id)
                prompt = response_selector.get_prompt('worries', session_id=session_id)
                return f"{trans} {prompt}"
            else:
                return response_selector.get_response('strengths', 'transition_advance', session_id)
        else:
            return response_selector.get_response('strengths', 'clarify', session_id)

def handle_worries_state(user_id: str, session_id: str, message: str, intent_result: dict, sentiment_result: dict) -> str:
    """Handle the worries state with progressive fallback"""
    intent = intent_result.get('label', 'unclear')
    user_sentiment = sentiment_result.get('label', 'neutral')
    
    if intent != 'unclear':
        reset_fsm_attempts(user_id, session_id)
        
        if advance_fsm_state(user_id, session_id):
            ack = response_selector.get_response('worries', 'acknowledgment', session_id, user_sentiment)
            prompt = response_selector.get_prompt('goals', session_id=session_id)
            return f"{ack} {prompt}"
        else:
            return response_selector.get_response('worries', 'acknowledgment', session_id, user_sentiment)
    else:
        increment_fsm_attempts(user_id, session_id)
        
        if should_force_advance(user_id, session_id):
            reset_fsm_attempts(user_id, session_id)
            
            if advance_fsm_state(user_id, session_id):
                trans = response_selector.get_response('worries', 'transition_advance', session_id)
                prompt = response_selector.get_prompt('goals', session_id=session_id)
                return f"{trans} {prompt}"
            else:
                return response_selector.get_response('worries', 'transition_advance', session_id)
        else:
            return response_selector.get_response('worries', 'clarify', session_id)

def handle_goals_state(user_id: str, session_id: str, message: str, intent_result: dict, sentiment_result: dict) -> str:
    """Handle the goals state - last step before LLM handoff"""
    intent = intent_result.get('label', 'unclear')
    user_sentiment = sentiment_result.get('label', 'neutral')
    
    if intent != 'unclear':
        reset_fsm_attempts(user_id, session_id)
        
        if advance_fsm_state(user_id, session_id):  # Move to 'llm_conversation' state
            ack = response_selector.get_response('goals', 'acknowledgment', session_id, user_sentiment)
            transition = "Great! Now we can have an open yarn about anything on your mind."
            return f"{ack} {transition}"
        else:
            return response_selector.get_response('goals', 'acknowledgment', session_id, user_sentiment)
    else:
        increment_fsm_attempts(user_id, session_id)
        
        if should_force_advance(user_id, session_id):
            reset_fsm_attempts(user_id, session_id)
            
            if advance_fsm_state(user_id, session_id):  # Move to 'llm_conversation' state
                trans = response_selector.get_response('goals', 'transition_advance', session_id)
                transition = "No worries! Let's move on and have a yarn about anything that's on your mind."
                return f"{trans} {transition}"
            else:
                return response_selector.get_response('goals', 'transition_advance', session_id)
        else:
            return response_selector.get_response('goals', 'clarify', session_id)

def handle_fallback_state(user_id: str, session_id: str, message: str, *args) -> str:
    """Handle unexpected FSM state"""
    current_state = get_fsm_state(user_id, session_id)
    logger.error(f"Router entered unexpected FSM state: {current_state} for session {session_id}")
    return response_selector.get_response('fallback', 'general', session_id)