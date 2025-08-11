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
from nlp.intent import classify_intent, get_intent_for_step
from nlp.preprocessor import normalize_text

from llm.fallback import LLMFallback
from database.repository import save_message

llm_fallback = LLMFallback()

def create_summary(responses):
    """Create a summary of the user's conversation responses"""
    summary = "Here's what we talked about today:\n\n"
    
    if responses.get('support_people'):
        summary += f"🤝 **Your Support People:** {responses['support_people']}\n\n"
    
    if responses.get('strengths'):
        summary += f"💪 **Your Strengths:** {responses['strengths']}\n\n"
    
    if responses.get('worries'):
        summary += f"💭 **What's On Your Mind:** {responses['worries']}\n\n"
    
    if responses.get('goals'):
        summary += f"🎯 **Your Goals:** {responses['goals']}\n\n"
    
    summary += "Remember: You have people who care about you and strengths to build on as you work towards your goals."
    
    return summary

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

    # Classify user intent and get expected intent for current step
    intent, confidence = classify_intent(normalized_message)
    expected_intent = get_intent_for_step(fsm.state)
    
    # Handle conversation flow with intent validation
    if fsm.is_welcome():
        # Welcome state - accept greetings or move forward
        if intent in ['greeting', 'affirmation'] or confidence > 0.5:
            fsm.next_step()
            reply = content['support_people']['prompt']
        else:
            # If unclear, provide welcome message
            reply = content.get('welcome', {}).get('prompt', "Hello! I'm here to support you through the Stay Strong approach. Ready to start?")
    
    elif fsm.is_support_people():
        # Support people step - validate user provided support information
        if intent == 'support_people' and confidence >= 0.3:
            # Good response about support people
            fsm.save_response(message)
            fsm.next_step()
            reply = content['strengths']['prompt']
        elif intent == 'negation' or 'no one' in normalized_message or 'nobody' in normalized_message:
            # User says they have no support - provide empathetic response
            fsm.save_response(message)
            reply = content.get('support_people', {}).get('no_support', 
                "That sounds tough. Sometimes support can come from unexpected places - maybe a teacher, community member, or even online communities. What about anyone who's been kind to you?")
        elif confidence < 0.3:
            # Low confidence - ask for clarification
            reply = content.get('support_people', {}).get('clarify', 
                "Tell me about the people in your life - family, friends, teachers, or anyone who cares about you.")
        else:
            # Try LLM fallback if enabled, otherwise clarify
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                reply = llm_fallback.get_reply(session_id, fsm.state, message)
            else:
                reply = content.get('support_people', {}).get('clarify', 
                    "I'd like to know about your support network. Who are the people you can turn to?")
    
    elif fsm.is_strengths():
        # Strengths step - validate user shared their strengths
        if intent == 'strengths' and confidence >= 0.3:
            # Good response about strengths
            fsm.save_response(message)
            fsm.next_step()
            reply = content['worries']['prompt']
        elif intent == 'negation' or 'nothing' in normalized_message or 'not good' in normalized_message:
            # User feels they have no strengths - provide encouragement
            reply = content.get('strengths', {}).get('encourage', 
                "Everyone has strengths, even if they're hard to see right now. Maybe you're a good listener, or you've gotten through tough times before. What's one small thing you do well?")
        elif confidence < 0.3:
            # Low confidence - ask for clarification
            reply = content.get('strengths', {}).get('clarify', 
                "What are you good at? It could be anything - sports, music, being kind, making people laugh, or getting through difficult times.")
        else:
            # Try LLM or provide clarification
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                reply = llm_fallback.get_reply(session_id, fsm.state, message)
            else:
                reply = content.get('strengths', {}).get('clarify', 
                    "Tell me about your strengths - what makes you proud or what you're good at.")
    
    elif fsm.is_worries():
        # Worries step - validate user shared their concerns
        if intent == 'worries' and confidence >= 0.3:
            # Good response about worries
            fsm.save_response(message)
            fsm.next_step()
            reply = content['goals']['prompt']
        elif intent == 'negation' or 'nothing' in normalized_message:
            # User says no worries - acknowledge and move on
            fsm.save_response("Nothing specific worrying me right now")
            fsm.next_step()
            reply = content['goals']['prompt']
        elif confidence < 0.3:
            # Low confidence - ask for clarification
            reply = content.get('worries', {}).get('clarify', 
                "What's been on your mind lately? Any concerns, stress, or challenges you're facing?")
        else:
            # Try LLM or provide clarification
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                reply = llm_fallback.get_reply(session_id, fsm.state, message)
            else:
                reply = content.get('worries', {}).get('clarify', 
                    "It's okay to share what's worrying you. What's been on your mind?")
    
    elif fsm.is_goals():
        # Goals step - validate user shared their goals
        if intent == 'goals' and confidence >= 0.3:
            # Good response about goals
            fsm.save_response(message)
            fsm.next_step()
            # Create summary with all responses
            responses = fsm.get_all_responses()
            summary_text = create_summary(responses)
            reply = f"{content['summary']['prompt']}\n\n{summary_text}"
        elif intent == 'unclear' or confidence < 0.3:
            # Low confidence - ask for clarification
            reply = content.get('goals', {}).get('clarify', 
                "What's one thing you'd like to work towards? It could be anything - big or small, short-term or long-term.")
        else:
            # Try LLM or provide clarification
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                reply = llm_fallback.get_reply(session_id, fsm.state, message)
            else:
                reply = content.get('goals', {}).get('clarify', 
                    "Tell me about your goals - what would you like to achieve or work towards?")
    
    elif fsm.is_summary():
        # Summary state - conversation complete, handle follow-up
        if intent in ['affirmation', 'greeting']:
            reply = content.get('summary', {}).get('thanks', 
                "Thank you for sharing with me today. Remember, you have people who support you and strengths to build on. Take care!")
        else:
            # Offer to restart or provide resources
            reply = content.get('summary', {}).get('followup', 
                "Would you like to go through the Stay Strong steps again, or do you need any support resources?")
    
    else:
        # Fallback for unexpected states
        reply = content.get('fallback', {}).get('prompt', 
            "I'm not sure how to help with that right now. Let's focus on the current step.")

    save_message(session_id, 'bot', reply)
    return reply
