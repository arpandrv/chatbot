# chatbot/aimhi-chatbot/core/router.py

import json
import logging
import time
import os

# --- Core Application Imports ---
from core.fsm import ChatBotFSM
from core.session import get_session

# --- Graceful Imports with Fallbacks ---
# This makes the router resilient even if some modules are missing or broken.

# Database (required for proper operation)
from database.repository_v2 import save_message, save_analytics_event, update_session_state

# LLM (optional - controlled by environment variable)
LLM_ENABLED = os.getenv('LLM_ENABLED', 'false').lower() == 'true'

if LLM_ENABLED:
    try:
        from llm.handoff_manager import LLMHandoffManager
        llm_handoff = LLMHandoffManager()
    except ImportError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"LLM enabled but import failed: {e}")
        raise  # Fail fast instead of limping along
else:
    llm_handoff = None

# NLP Components
from nlp.risk_detector import contains_risk, get_crisis_resources
from nlp.intent_distilbert import classify_intent
from nlp.preprocessor import normalize_text
from nlp.response_selector import VariedResponseSelector
from nlp.sentiment import analyze_sentiment

# --- Component Initialization ---
logger = logging.getLogger(__name__)
response_selector = VariedResponseSelector()

# LLM manager initialized above based on LLM_ENABLED


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
        save_message(session_id, 'user', message)
        normalized_message = normalize_text(message)
        debug_info['normalized_message'] = normalized_message

        # --- Step 2: Universal Risk Detection (Highest Priority) ---
        if contains_risk(normalized_message):
            logger.warning(f"Risk detected in session {session_id}.")
            reply = get_crisis_resources()
            debug_info.update({'risk_detected': True, 'response_source': 'crisis_resources'})
            save_analytics_event('risk_triggered', {'session_id': session_id})
            save_message(session_id, 'bot', json.dumps({'type': 'crisis_resources', 'content': reply}))
            return reply, debug_info

        # --- Step 3: Get Session & FSM State ---
        session = get_session(session_id)
        fsm = session['fsm']
        debug_info['fsm_state_before'] = fsm.state

        # --- Step 4: State-Dependent Logic Branching ---
        # This is the core architectural improvement: separate FSM logic from LLM logic.
        
        if fsm.state in ['summary', 'llm_conversation']:
            # --- Branch A: LLM-Driven Conversation ---
            reply = _handle_llm_conversation(session_id, fsm, message, debug_info)
        else:
            # --- Branch B: FSM-Driven Conversation ---
            reply = _handle_fsm_conversation(session_id, fsm, message, debug_info)

        # --- Step 5: Finalization ---
        debug_info['fsm_state_after'] = fsm.state
        save_message(session_id, 'bot', reply)

    except Exception as e:
        logger.error(f"Unhandled error in router for session {session_id}: {e}", exc_info=True)
        debug_info['errors'].append(f"router_fatal_error: {str(e)}")
        reply = response_selector.get_response('fallback', 'general', session_id)

    debug_info['processing_time_ms'] = int((time.time() - start_time) * 1000)
    return reply, debug_info


# --- Logic Handlers for Each Branch ---

def _handle_fsm_conversation(session_id: str, fsm: ChatBotFSM, message: str, debug_info: dict) -> str:
    """Handles all logic for the structured, FSM-driven part of the chat."""
    
    # Get the current state before any transitions
    current_state = fsm.state
    
    # Run expensive NLP models only when needed for FSM logic.
    try:
        intent_result = classify_intent(message, current_step=fsm.state)
        sentiment_result = analyze_sentiment(message)
        debug_info['intent_classification'] = intent_result
        debug_info['user_sentiment'] = sentiment_result
    except Exception as e:
        logger.error(f"NLP processing failed in FSM state {fsm.state}: {e}", exc_info=True)
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
    handler = state_handlers.get(fsm.state, _handle_fallback_state)
    response = handler(session_id, fsm, message, intent_result, sentiment_result, debug_info)
    
    # If state changed, persist to database
    if fsm.state != current_state:
        update_session_state(session_id, fsm.state)
        logger.debug(f"Session {session_id} advanced: {current_state} -> {fsm.state}")
        debug_info['state_transition'] = f"{current_state} -> {fsm.state}"
    
    return response


def _handle_llm_conversation(session_id: str, fsm: ChatBotFSM, message: str, debug_info: dict) -> str:
    """Handles all logic for the free-form, LLM-driven part of the chat."""
    # Transition to the dedicated LLM state if this is the first turn after the summary.
    if fsm.state == 'summary':
        if fsm.can_advance():
            fsm.start_llm_chat()
            update_session_state(session_id, fsm.state)
            debug_info['response_source'] = 'llm_handoff_initial'
        else:
            logger.warning(f"Cannot transition from summary to LLM for session {session_id}")
            debug_info['errors'].append("invalid_llm_transition")
            return response_selector.get_response('summary', 'closing', session_id)
    else:
        debug_info['response_source'] = 'llm_handoff_ongoing'

    # Log an analytics event for every single turn in the LLM phase.
    save_analytics_event('llm_turn_completed', {'session_id': session_id})
    
    if not llm_handoff:
        debug_info['errors'].append("llm_not_available")
        return response_selector.get_response('summary', 'closing', session_id)

    try:
        reply = llm_handoff.handle_llm_response_sync(session_id, message)
    except Exception as e:
        logger.error(f"LLM handoff failed for session {session_id}: {e}", exc_info=True)
        debug_info['errors'].append(f"llm_error: {type(e).__name__}")
        reply = response_selector.get_response('fallback', 'general', session_id)

    return reply


# --- Individual FSM State Handlers ---

def _handle_welcome_state(session_id, fsm, message, intent_result, sentiment_result, debug_info):
    """Handle the welcome state - entry point of conversation"""
    intent, confidence, user_sentiment = intent_result['label'], intent_result.get('confidence', 0.0), sentiment_result['label']
    
    if len(message.strip()) > 3:  # Any substantial response moves the conversation forward
        if fsm.can_advance():
            fsm.next_step()
            update_session_state(session_id, fsm.state)
            debug_info['response_source'] = 'welcome_advance'
            return response_selector.get_response('welcome', 'ready_response', session_id, user_sentiment)
        else:
            logger.error(f"Cannot advance from welcome state for session {session_id}")
            return response_selector.get_response('welcome', 'greeting', session_id, user_sentiment)
    else:
        debug_info['response_source'] = 'welcome_greeting'
        return response_selector.get_response('welcome', 'greeting', session_id, user_sentiment)


def _handle_support_people_state(session_id, fsm, message, intent_result, sentiment_result, debug_info):
    """Handle the support_people state with progressive fallback"""
    intent, user_sentiment = intent_result['label'], sentiment_result['label']

    # Check if intent is clear (not unclear)
    if intent != 'unclear':
        # Clear response - save and advance
        fsm.save_response(message)
        fsm.reset_attempts()
        
        if fsm.can_advance():
            fsm.next_step()
            update_session_state(session_id, fsm.state)
            debug_info['response_source'] = 'support_people_advance'
            ack = response_selector.get_response('support_people', 'acknowledgment', session_id, user_sentiment)
            prompt = response_selector.get_prompt('strengths', session_id=session_id)
            return f"{ack} {prompt}"
        else:
            logger.error(f"Cannot advance from support_people state for session {session_id}")
            return response_selector.get_response('support_people', 'acknowledgment', session_id, user_sentiment)
    else:
        # Unclear response - use progressive fallback
        fsm.increment_attempt()
        debug_info['attempt_count'] = fsm.get_attempt_count()
        
        if fsm.should_advance():
            # After 2 attempts, save unclear response and move forward
            fsm.save_response(f"Unclear: {message}")
            fsm.reset_attempts()
            
            if fsm.can_advance():
                fsm.next_step()
                update_session_state(session_id, fsm.state)
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


def _handle_strengths_state(session_id, fsm, message, intent_result, sentiment_result, debug_info):
    """Handle the strengths state with progressive fallback"""
    intent, user_sentiment = intent_result['label'], sentiment_result['label']
    
    if intent != 'unclear':
        # Good response - save and advance
        fsm.save_response(message)
        fsm.reset_attempts()
        
        if fsm.can_advance():
            fsm.next_step()
            update_session_state(session_id, fsm.state)
            debug_info['response_source'] = 'strengths_advance'
            ack = response_selector.get_response('strengths', 'acknowledgment', session_id, user_sentiment)
            prompt = response_selector.get_prompt('worries', session_id=session_id)
            return f"{ack} {prompt}"
        else:
            logger.error(f"Cannot advance from strengths state for session {session_id}")
            return response_selector.get_response('strengths', 'acknowledgment', session_id, user_sentiment)
    else:
        # Unclear response - use progressive fallback
        fsm.increment_attempt()
        debug_info['attempt_count'] = fsm.get_attempt_count()
        
        if fsm.should_advance():
            # After 2 attempts, save unclear response and move forward
            fsm.save_response(f"Unclear: {message}")
            fsm.reset_attempts()
            
            if fsm.can_advance():
                fsm.next_step()
                update_session_state(session_id, fsm.state)
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


def _handle_worries_state(session_id, fsm, message, intent_result, sentiment_result, debug_info):
    """Handle the worries state with progressive fallback"""
    intent, user_sentiment = intent_result['label'], sentiment_result['label']
    
    if intent != 'unclear':
        # Good response - save and advance
        fsm.save_response(message)
        fsm.reset_attempts()
        
        if fsm.can_advance():
            fsm.next_step()
            update_session_state(session_id, fsm.state)
            debug_info['response_source'] = 'worries_advance'
            ack = response_selector.get_response('worries', 'acknowledgment', session_id, user_sentiment)
            prompt = response_selector.get_prompt('goals', session_id=session_id)
            return f"{ack} {prompt}"
        else:
            logger.error(f"Cannot advance from worries state for session {session_id}")
            return response_selector.get_response('worries', 'acknowledgment', session_id, user_sentiment)
    else:
        # Unclear response - use progressive fallback
        fsm.increment_attempt()
        debug_info['attempt_count'] = fsm.get_attempt_count()
        
        if fsm.should_advance():
            # After 2 attempts, save unclear response and move forward
            fsm.save_response(f"Unclear: {message}")
            fsm.reset_attempts()
            
            if fsm.can_advance():
                fsm.next_step()
                update_session_state(session_id, fsm.state)
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


def _handle_goals_state(session_id, fsm, message, intent_result, sentiment_result, debug_info):
    """Handle the goals state - last step before summary"""
    intent, user_sentiment = intent_result['label'], sentiment_result['label']
    
    if intent != 'unclear':
        # Good response - save and advance to summary
        fsm.save_response(message)
        fsm.reset_attempts()
        
        if fsm.can_advance():
            fsm.next_step()  # Move to 'summary'
            update_session_state(session_id, fsm.state)
            debug_info['response_source'] = 'goals_to_summary'
            
            # Generate summary with all responses
            ack = response_selector.get_response('goals', 'acknowledgment', session_id, user_sentiment)
            summary_prompt = response_selector.get_prompt('summary', 'prompt', session_id=session_id)
            
            # Include the actual responses in the summary if available
            responses = fsm.get_all_responses()
            summary_content = _generate_summary_content(responses)
            
            closing = response_selector.get_response('summary', 'closing', session_id)
            followup = response_selector.get_response('summary', 'followup', session_id)
            
            return f"{ack} {summary_prompt}\n\n{summary_content}\n\n{closing} {followup}"
        else:
            logger.error(f"Cannot advance from goals state for session {session_id}")
            return response_selector.get_response('goals', 'acknowledgment', session_id, user_sentiment)
    else:
        # Unclear response - use progressive fallback
        fsm.increment_attempt()
        debug_info['attempt_count'] = fsm.get_attempt_count()
        
        if fsm.should_advance():
            # After 2 attempts, save unclear response and move to summary
            fsm.save_response(f"Unclear: {message}")
            fsm.reset_attempts()
            
            if fsm.can_advance():
                fsm.next_step()  # Move to 'summary'
                update_session_state(session_id, fsm.state)
                debug_info['response_source'] = 'goals_force_to_summary'
                
                trans = response_selector.get_response('goals', 'transition_advance', session_id)
                summary_prompt = response_selector.get_prompt('summary', 'prompt', session_id=session_id)
                
                responses = fsm.get_all_responses()
                summary_content = _generate_summary_content(responses)
                
                closing = response_selector.get_response('summary', 'closing', session_id)
                return f"{trans} {summary_prompt}\n\n{summary_content}\n\n{closing}"
            else:
                return response_selector.get_response('goals', 'transition_advance', session_id)
        else:
            # First attempt - ask for clarification
            debug_info['response_source'] = 'goals_clarify'
            return response_selector.get_response('goals', 'clarify', session_id)


def _handle_fallback_state(session_id, fsm, *args):
    """Handles any unexpected FSM state."""
    logger.error(f"Router entered unexpected FSM state: {fsm.state} for session {session_id}")
    return response_selector.get_response('fallback', 'general', session_id)


def _generate_summary_content(responses: dict) -> str:
    """Generate a formatted summary of the user's responses"""
    summary_parts = []
    
    if responses.get('support_people'):
        summary_parts.append(f"**Support People:** {responses['support_people']}")
    
    if responses.get('strengths'):
        summary_parts.append(f"**Strengths:** {responses['strengths']}")
    
    if responses.get('worries'):
        summary_parts.append(f"**Worries:** {responses['worries']}")
    
    if responses.get('goals'):
        summary_parts.append(f"**Goals:** {responses['goals']}")
    
    if summary_parts:
        return "Here's what we talked about today:\n\n" + "\n".join(summary_parts)
    else:
        return "Thanks for having this yarn with me today."