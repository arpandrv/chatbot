# chatbot/aimhi-chatbot/core/router.py

import json
import logging
import time
import os

# --- Core Application Imports ---
from core.fsm import (create_fsm, get_state, advance_state, can_advance,
                      save_response, increment_attempt, get_attempt_count,
                      should_force_advance, reset_attempts)
from core.session import validate_session, touch_session

# --- Graceful Imports with Fallbacks ---
# This makes the router resilient even if some modules are missing or broken.

# Database (required for proper operation)
# TODO: Supabase Migration - Feature flag for database provider
DATABASE_PROVIDER = os.getenv('DATABASE_PROVIDER', 'sqlite')  # 'sqlite' or 'supabase'

# TODO: Database imports removed during migration cleanup
# Database operations will be replaced with Supabase calls after migration

def save_message(session_id: str, role: str, message: str):
    """TODO: Replace with Supabase call"""
    pass

def save_analytics_event(event_type: str, metadata: dict):
    """TODO: Replace with Supabase call"""
    pass

def update_session_state(session_id: str, state: str):
    """TODO: Replace with Supabase call"""
    pass

# LLM (optional - controlled by environment variable)
LLM_ENABLED = os.getenv('LLM_ENABLED', 'false').lower() == 'true'

if LLM_ENABLED:
    try:
        from llm.handoff_manager import handle_llm_response
        llm_handoff = None  # Using functional approach now
    except ImportError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"LLM enabled but import failed: {e}")
        raise  # Fail fast instead of limping along
else:
    llm_handoff = None

# NLP Components
from nlp.risk_detector import contains_risk, get_crisis_resources
from nlp.intent_roberta_zeroshot import classify_intent
from nlp.preprocessor import normalize_text
from nlp.response_selector import VariedResponseSelector
from nlp.sentiment import analyze_sentiment

# --- Component Initialization ---
logger = logging.getLogger(__name__)
response_selector = VariedResponseSelector()

# FSM storage - in-memory cache of active FSMs
_fsm_cache = {}  # {session_id: fsm_data}

def get_or_create_fsm(session_id: str) -> dict:
    """Get existing FSM or create new one for session."""
    if session_id not in _fsm_cache:
        # Create new FSM at welcome state
        _fsm_cache[session_id] = create_fsm(session_id, initial_state='welcome')
        logger.info(f"Created new FSM for session {session_id}")
        
        # TODO: Supabase Migration - Session state restoration
        # try:
        #     from config.supabase import supabase
        #     db_session = supabase.table('sessions').select('fsm_state').eq('session_id', session_id).single().execute()
        #     if db_session.data:
        #         _fsm_cache[session_id]['machine'].state = db_session.data['fsm_state']
        #         logger.info(f"Restored FSM state for {session_id}: {db_session.data['fsm_state']}")
        #     else:
        #         supabase.table('sessions').insert({'session_id': session_id, 'fsm_state': 'welcome'}).execute()
        # except Exception as e:
        #     logger.warning(f"Could not check database for session {session_id}: {e}")
        
        logger.info(f"Session state restoration skipped during migration for {session_id}")
    
    return _fsm_cache[session_id]

# LLM manager initialized above based on LLM_ENABLED

def get_current_state(session_id: str) -> str:
    """Get current FSM state for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Current FSM state or 'unknown' if session doesn't exist
    """
    if session_id in _fsm_cache:
        return get_state(_fsm_cache[session_id])
    return 'unknown'


# --- Main Router Function ---
def route_message(session_id: str, message: str) -> tuple[str, dict]:
    """
    Main routing function. Processes a user message and returns a response and debug info.
    This function orchestrates the entire response generation pipeline.
    """
    start_time = time.time()
    debug_info = {
        'risk_detected': False,
        'fsm_state_before': 'unknown',
        'fsm_state_after': 'unknown',
        'response_source': 'unhandled',
        'errors': []
    }

    try:
        # --- Step 1: Persist User Message & Normalize ---
        # TODO: Supabase Migration - Simple single-line call instead of transaction management
        save_message(session_id, 'user', message)
        normalized_message = normalize_text(message)
        debug_info['normalized_message'] = normalized_message

        # --- Step 2: Universal Risk Detection (Highest Priority) ---
        if contains_risk(normalized_message):
            logger.warning(f"Risk detected in session {session_id}.")
            reply = get_crisis_resources()
            debug_info.update({'risk_detected': True, 'response_source': 'crisis_resources'})
            # TODO: Supabase Migration - Analytics events will be much simpler with built-in dashboards
            save_analytics_event('risk_triggered', {'session_id': session_id})
            save_message(session_id, 'bot', json.dumps({'type': 'crisis_resources', 'content': reply}))
            return reply, debug_info

        # --- Step 3: Get or Create FSM ---
        # Update session activity tracking
        touch_session(session_id)
        
        # Get FSM (creates if doesn't exist)
        fsm_data = get_or_create_fsm(session_id)
        debug_info['fsm_state_before'] = get_state(fsm_data)

        # --- Step 4: State-Dependent Logic Branching ---
        # This is the core architectural improvement: separate FSM logic from LLM logic.
        
        if get_state(fsm_data) in ['llm_conversation']:
            # --- Branch A: LLM-Driven Conversation ---
            reply = _handle_llm_conversation(session_id, fsm_data, message, debug_info)
        else:
            # --- Branch B: FSM-Driven Conversation ---
            reply = _handle_fsm_conversation(session_id, fsm_data, message, debug_info)

        # --- Step 5: Finalization ---
        debug_info['fsm_state_after'] = get_state(fsm_data)
        save_message(session_id, 'bot', reply)

    except Exception as e:
        logger.error(f"Unhandled error in router for session {session_id}: {e}", exc_info=True)
        debug_info['errors'].append(f"router_fatal_error: {str(e)}")
        reply = response_selector.get_response('fallback', 'general', session_id)

    debug_info['processing_time_ms'] = int((time.time() - start_time) * 1000)
    return reply, debug_info


# --- Logic Handlers for Each Branch ---

def _handle_fsm_conversation(session_id: str, fsm_data: dict, message: str, debug_info: dict) -> str:
    """Handles all logic for the structured, FSM-driven part of the chat."""
    
    # Get the current state before any transitions
    current_state = get_state(fsm_data)
    
    # Run expensive NLP models only when needed for FSM logic.
    try:
        intent_result = classify_intent(message, current_step=get_state(fsm_data))
        sentiment_result = analyze_sentiment(message)
        debug_info['intent_classification'] = intent_result
        debug_info['user_sentiment'] = sentiment_result
    except Exception as e:
        logger.error(f"NLP processing failed in FSM state {get_state(fsm_data)}: {e}", exc_info=True)
        debug_info['errors'].append("nlp_pipeline_error")
        # Provide a safe fallback if NLP fails
        return response_selector.get_response('fallback', 'clarification', session_id)

    # Delegate to the appropriate state handler function
    state_handlers = {
        'welcome': _handle_welcome_state,
        'support_people': _handle_support_people_state,
        'strengths': _handle_strengths_state,
        'worries': _handle_worries_state,
        'goals': _handle_goals_state,
    }
    handler = state_handlers.get(get_state(fsm_data), _handle_fallback_state)
    response = handler(session_id, fsm_data, message, intent_result, sentiment_result, debug_info)
    
    # If state changed, persist to database
    new_state = get_state(fsm_data)
    if new_state != current_state:
        # TODO: Supabase Migration - State updates will be atomic and faster
        update_session_state(session_id, new_state)
        logger.debug(f"Session {session_id} advanced: {current_state} -> {new_state}")
        debug_info['state_transition'] = f"{current_state} -> {new_state}"
    
    return response


def _handle_llm_conversation(session_id: str, fsm_data: dict, message: str, debug_info: dict) -> str:
    """Handles all logic for the free-form, LLM-driven part of the chat."""
    debug_info['response_source'] = 'llm_handoff_ongoing'

    # Log an analytics event for every single turn in the LLM phase.
    # TODO: Supabase Migration - Real-time analytics will be available through dashboard
    save_analytics_event('llm_turn_completed', {'session_id': session_id})
    
    if not LLM_ENABLED:
        debug_info['errors'].append("llm_not_available")
        return "I'm not able to continue our conversation right now. Please try again later."

    try:
        # TODO: Fetch full conversation data here and pass to handoff_manager
        # Updated handoff_manager now takes FULL conversation including current message
        # New signature: llm_handoff.handle_llm_response(full_conversation)
        # where full_conversation = [{"role": "user", "message": "..."}, {"role": "bot", "message": "..."}, ...]
        # Router should query database for ALL messages in session including the current one
        # No more splitting into conversation_history + current_message
        # No more FSM context extraction (redundant - already in conversation)
        
        # TEMPORARY: Keep old signature until database logic is implemented here
        # reply = handle_llm_response(full_conversation)
        reply = "LLM handoff not yet implemented with new architecture"
    except Exception as e:
        logger.error(f"LLM handoff failed for session {session_id}: {e}", exc_info=True)
        debug_info['errors'].append(f"llm_error: {type(e).__name__}")
        reply = response_selector.get_response('fallback', 'general', session_id)

    return reply


# --- Individual FSM State Handlers ---

def _handle_welcome_state(session_id, fsm_data, message, intent_result, sentiment_result, debug_info):
    """Handle the welcome state - entry point of conversation"""
    intent, confidence, user_sentiment = intent_result['label'], intent_result.get('confidence', 0.0), sentiment_result['label']
    
    # Log intent classification for debugging
    debug_info['intent_classification'] = {'intent': intent, 'confidence': confidence}
    
    if len(message.strip()) > 3:  # Any substantial response moves the conversation forward
        if can_advance(fsm_data):
            advance_state(fsm_data)
            update_session_state(session_id, get_state(fsm_data))
            debug_info['response_source'] = 'welcome_advance'
            return response_selector.get_response('welcome', 'ready_response', session_id, user_sentiment)
        else:
            logger.error(f"Cannot advance from welcome state for session {session_id}")
            return response_selector.get_response('welcome', 'greeting', session_id, user_sentiment)
    else:
        debug_info['response_source'] = 'welcome_greeting'
        return response_selector.get_response('welcome', 'greeting', session_id, user_sentiment)


def _handle_support_people_state(session_id, fsm_data, message, intent_result, sentiment_result, debug_info):
    """Handle the support_people state with progressive fallback"""
    intent, user_sentiment = intent_result['label'], sentiment_result['label']

    # Check if intent is clear (not unclear)
    if intent != 'unclear':
        # Clear response - save and advance
        save_response(fsm_data(message)
        reset_attempts(fsm_data)
        
        if can_advance(fsm_data):
            advance_state(fsm_data)
            update_session_state(session_id, get_state(fsm_data))
            debug_info['response_source'] = 'support_people_advance'
            ack = response_selector.get_response('support_people', 'acknowledgment', session_id, user_sentiment)
            prompt = response_selector.get_prompt('strengths', session_id=session_id)
            return f"{ack} {prompt}"
        else:
            logger.error(f"Cannot advance from support_people state for session {session_id}")
            return response_selector.get_response('support_people', 'acknowledgment', session_id, user_sentiment)
    else:
        # Unclear response - use progressive fallback
        increment_attempt(fsm_data)
        debug_info['attempt_count'] = get_attempt_count(fsm_data)
        
        if should_force_advance(fsm_data):
            # After 2 attempts, save unclear response and move forward
            save_response(fsm_data(f"Unclear: {message}")
            reset_attempts(fsm_data)
            
            if can_advance(fsm_data):
                advance_state(fsm_data)
                update_session_state(session_id, get_state(fsm_data))
                debug_info['response_source'] = 'support_people_force_advance'
                trans = response_selector.get_response('support_people', 'transition_unclear', session_id)
                prompt = response_selector.get_prompt('strengths', session_id=session_id)
                return f"{trans} {prompt}"
            else:
                return response_selector.get_response('support_people', 'transition_unclear', session_id)
        else:
            # First attempt - ask for clarification
            debug_info['response_source'] = 'support_people_clarify'
            return response_selector.get_response('support_people', 'clarify', session_id)


def _handle_strengths_state(session_id, fsm_data, message, intent_result, sentiment_result, debug_info):
    """Handle the strengths state with progressive fallback"""
    intent, user_sentiment = intent_result['label'], sentiment_result['label']
    
    if intent != 'unclear':
        # Good response - save and advance
        save_response(fsm_data(message)
        reset_attempts(fsm_data)
        
        if can_advance(fsm_data):
            advance_state(fsm_data)
            update_session_state(session_id, get_state(fsm_data))
            debug_info['response_source'] = 'strengths_advance'
            ack = response_selector.get_response('strengths', 'acknowledgment', session_id, user_sentiment)
            prompt = response_selector.get_prompt('worries', session_id=session_id)
            return f"{ack} {prompt}"
        else:
            logger.error(f"Cannot advance from strengths state for session {session_id}")
            return response_selector.get_response('strengths', 'acknowledgment', session_id, user_sentiment)
    else:
        # Unclear response - use progressive fallback
        increment_attempt(fsm_data)
        debug_info['attempt_count'] = get_attempt_count(fsm_data)
        
        if should_force_advance(fsm_data):
            # After 2 attempts, save unclear response and move forward
            save_response(fsm_data(f"Unclear: {message}")
            reset_attempts(fsm_data)
            
            if can_advance(fsm_data):
                advance_state(fsm_data)
                update_session_state(session_id, get_state(fsm_data))
                debug_info['response_source'] = 'strengths_force_advance'
                trans = response_selector.get_response('strengths', 'transition_advance', session_id)
                prompt = response_selector.get_prompt('worries', session_id=session_id)
                return f"{trans} {prompt}"
            else:
                return response_selector.get_response('strengths', 'transition_advance', session_id)
        else:
            # First attempt - encourage response
            debug_info['response_source'] = 'strengths_clarify'
            return response_selector.get_response('strengths', 'clarify', session_id)


def _handle_worries_state(session_id, fsm_data, message, intent_result, sentiment_result, debug_info):
    """Handle the worries state with progressive fallback"""
    intent, user_sentiment = intent_result['label'], sentiment_result['label']
    
    if intent != 'unclear':
        # Good response - save and advance
        save_response(fsm_data(message)
        reset_attempts(fsm_data)
        
        if can_advance(fsm_data):
            advance_state(fsm_data)
            update_session_state(session_id, get_state(fsm_data))
            debug_info['response_source'] = 'worries_advance'
            ack = response_selector.get_response('worries', 'acknowledgment', session_id, user_sentiment)
            prompt = response_selector.get_prompt('goals', session_id=session_id)
            return f"{ack} {prompt}"
        else:
            logger.error(f"Cannot advance from worries state for session {session_id}")
            return response_selector.get_response('worries', 'acknowledgment', session_id, user_sentiment)
    else:
        # Unclear response - use progressive fallback
        increment_attempt(fsm_data)
        debug_info['attempt_count'] = get_attempt_count(fsm_data)
        
        if should_force_advance(fsm_data):
            # After 2 attempts, save unclear response and move forward
            save_response(fsm_data(f"Unclear: {message}")
            reset_attempts(fsm_data)
            
            if can_advance(fsm_data):
                advance_state(fsm_data)
                update_session_state(session_id, get_state(fsm_data))
                debug_info['response_source'] = 'worries_force_advance'
                trans = response_selector.get_response('worries', 'transition_advance', session_id)
                prompt = response_selector.get_prompt('goals', session_id=session_id)
                return f"{trans} {prompt}"
            else:
                return response_selector.get_response('worries', 'transition_advance', session_id)
        else:
            # First attempt - ask for clarification
            debug_info['response_source'] = 'worries_clarify'
            return response_selector.get_response('worries', 'clarify', session_id)


def _handle_goals_state(session_id, fsm_data, message, intent_result, sentiment_result, debug_info):
    """Handle the goals state - last step before LLM handoff"""
    intent, user_sentiment = intent_result['label'], sentiment_result['label']
    
    if intent != 'unclear':
        # Good response - save and advance to LLM handoff
        save_response(fsm_data(message)
        reset_attempts(fsm_data)
        
        if fsm.can_advance():
            fsm.next_step()  # Move to 'llm_conversation' state
            update_session_state(session_id, fsm.state)
            debug_info['response_source'] = 'goals_to_llm_handoff'
            
            # Acknowledge and transition to open conversation
            ack = response_selector.get_response('goals', 'acknowledgment', session_id, user_sentiment)
            transition = "Great! Now we can have an open yarn about anything on your mind."
            
            return f"{ack} {transition}"
        else:
            logger.error(f"Cannot advance from goals state for session {session_id}")
            return response_selector.get_response('goals', 'acknowledgment', session_id, user_sentiment)
    else:
        # Unclear response - use progressive fallback
        increment_attempt(fsm_data)
        debug_info['attempt_count'] = get_attempt_count(fsm_data)
        
        if should_force_advance(fsm_data):
            # After 2 attempts, save unclear response and move to LLM handoff
            save_response(fsm_data(f"Unclear: {message}")
            reset_attempts(fsm_data)
            
            if fsm.can_advance():
                fsm.next_step()  # Move to 'llm_conversation' state
                update_session_state(session_id, fsm.state)
                debug_info['response_source'] = 'goals_force_to_llm_handoff'
                
                trans = response_selector.get_response('goals', 'transition_advance', session_id)
                transition = "No worries! Let's move on and have a yarn about anything that's on your mind."
                
                return f"{trans} {transition}"
            else:
                return response_selector.get_response('goals', 'transition_advance', session_id)
        else:
            # First attempt - ask for clarification
            debug_info['response_source'] = 'goals_clarify'
            return response_selector.get_response('goals', 'clarify', session_id)


def _handle_fallback_state(session_id, fsm_data, *args):
    """Handles any unexpected FSM state."""
    logger.error(f"Router entered unexpected FSM state: {get_state(fsm_data)} for session {session_id}")
    logger.debug(f"Fallback handler received args: {args}")
    return response_selector.get_response('fallback', 'general', session_id)


