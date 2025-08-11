from core.fsm import ChatBotFSM
from core.session import get_session
import json
import os

# Construct the absolute path to the config file
script_dir = os.path.dirname(__file__)
config_path = os.path.join(script_dir, '..', 'config', 'content.json')

with open(config_path) as f:
    content = json.load(f)

from nlp.risk_detector import contains_risk, get_crisis_resources
from nlp.intent import classify_intent
from nlp.preprocessor import normalize_text

from llm.fallback import LLMFallback
from database.repository import save_message

llm_fallback = LLMFallback()

def route_message(session_id, message):
    save_message(session_id, 'user', message)
    normalized_message = normalize_text(message)

    # Priority 1: Risk detection
    if contains_risk(normalized_message):
        reply = get_crisis_resources()
        save_message(session_id, 'bot', json.dumps(reply))
        return reply

    session = get_session(session_id)
    fsm = session['fsm']

    # Check intent classification
    intent, confidence = classify_intent(normalized_message)

    # If LLM is enabled and confidence is low, use LLM fallback
    if os.getenv('LLM_ENABLED', 'false').lower() == 'true' and confidence < 0.4:
        reply = llm_fallback.get_reply(session_id, fsm.state, message)
        save_message(session_id, 'bot', reply)
        return reply

    # Basic routing logic - moves through FSM states
    if fsm.is_welcome():
        fsm.next_step()
        reply = content['support_people']['prompt']
    elif fsm.is_support_people():
        fsm.next_step()
        reply = content['strengths']['prompt']
    elif fsm.is_strengths():
        fsm.next_step()
        reply = content['worries']['prompt']
    elif fsm.is_worries():
        fsm.next_step()
        reply = content['goals']['prompt']
    elif fsm.is_goals():
        fsm.next_step()
        reply = content['summary']['prompt']
    else:
        reply = content['fallback']['prompt']

    save_message(session_id, 'bot', reply)
    return reply
