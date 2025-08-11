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
    # Use original message for intent classification to preserve natural language patterns
    # Pass current FSM state for context-aware classification
    intent, confidence = classify_intent(message, current_step=fsm.state)
    expected_intent = get_intent_for_step(fsm.state)
    
    # Handle conversation flow with intent validation
    if fsm.is_welcome():
        # Welcome state - handle initial interaction more gradually
        if intent == 'greeting':
            # First greeting - give welcome message, stay in welcome state
            reply = content.get('welcome', {}).get('prompt', "G'day! Good to meet you 😊 Ready for a yarn about your wellbeing?")
        elif intent in ['affirmation'] or (confidence > 0.6 and intent in ['greeting', 'affirmation']):
            # User is ready to proceed - advance to support_people
            fsm.next_step()
            reply = content['support_people']['prompt']
        else:
            # Unclear or first visit - provide welcome message
            reply = content.get('welcome', {}).get('prompt', "G'day! I'm here to have a supportive yarn with you. Ready to start?")
    
    elif fsm.is_support_people():
        # Support people step - validate user provided support information
        if intent == 'support_people' and confidence >= 0.2:
            # Good response about support people
            fsm.save_response(message)
            fsm.next_step()
            reply = content['strengths']['prompt']
        elif intent == 'negation' and ('no one' in normalized_message or 'nobody' in normalized_message or 'no support' in normalized_message):
            # User explicitly says they have no support - provide empathetic response
            fsm.save_response(message)
            reply = content.get('support_people', {}).get('no_support', 
                "That sounds tough. Sometimes support can come from unexpected places - maybe a teacher, community member, or even online communities. What about anyone who's been kind to you?")
        elif intent == 'affirmation' and fsm.get_attempt_count() > 0:
            # User chose to move on after being offered choice
            fsm.save_response("Preferred not to discuss support people in detail")
            fsm.next_step()
            reply = f"{content['support_people']['acknowledge_move']} {content['strengths']['prompt']}"
        elif confidence < 0.2 or intent == 'unclear':
            # Low confidence or unclear response - implement progressive fallback
            fsm.increment_attempt()
            if fsm.should_offer_choice():
                # First attempt failed - offer choice
                reply = content.get('support_people', {}).get('offer_choice', 
                    "I hear what you're saying, and that's completely valid. Would you like to think about support people a bit more, or shall we move on and yarn about your strengths instead?")
            elif fsm.should_force_advance():
                # Second attempt failed - acknowledge and move on
                fsm.save_response("Had difficulty articulating support people")
                fsm.next_step()
                reply = f"{content['support_people']['acknowledge_move']} {content['strengths']['prompt']}"
            else:
                # Initial clarification attempt
                reply = content.get('support_people', {}).get('clarify', 
                    "Tell me about the people in your life - family, friends, teachers, or anyone who cares about you.")
        else:
            # Try LLM fallback if enabled, otherwise use progressive fallback
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                reply = llm_fallback.get_reply(session_id, fsm.state, message)
            else:
                fsm.increment_attempt()
                if fsm.should_offer_choice():
                    reply = content.get('support_people', {}).get('offer_choice', 
                        "I hear what you're saying, and that's completely valid. Would you like to think about support people a bit more, or shall we move on and yarn about your strengths instead?")
                elif fsm.should_force_advance():
                    fsm.save_response("Had difficulty articulating support people")
                    fsm.next_step()
                    reply = f"{content['support_people']['acknowledge_move']} {content['strengths']['prompt']}"
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
        elif intent == 'negation' and ('nothing' in normalized_message or 'not good' in normalized_message or 'no strengths' in normalized_message):
            # User explicitly feels they have no strengths - provide encouragement
            reply = content.get('strengths', {}).get('encourage', 
                "Everyone has strengths, even if they're hard to see right now. Maybe you're a good listener, or you've gotten through tough times before. What's one small thing you do well?")
        elif intent == 'affirmation' and fsm.get_attempt_count() > 0:
            # User chose to move on after being offered choice
            fsm.save_response("Preferred not to discuss strengths in detail")
            fsm.next_step()
            reply = f"{content['strengths']['acknowledge_move']} {content['worries']['prompt']}"
        elif confidence < 0.2 or intent == 'unclear':
            # Low confidence or unclear response - implement progressive fallback
            fsm.increment_attempt()
            if fsm.should_offer_choice():
                # First attempt failed - offer choice
                reply = content.get('strengths', {}).get('offer_choice', 
                    "I hear you, and sometimes it's hard to see our own strengths. Would you like to keep thinking about this, or shall we move on to talk about what's been on your mind?")
            elif fsm.should_force_advance():
                # Second attempt failed - acknowledge and move on
                fsm.save_response("Had difficulty articulating strengths")
                fsm.next_step()
                reply = f"{content['strengths']['acknowledge_move']} {content['worries']['prompt']}"
            else:
                # Initial clarification attempt
                reply = content.get('strengths', {}).get('clarify', 
                    "What are you good at? It could be anything - sports, music, being kind, making people laugh, or getting through difficult times.")
        else:
            # Try LLM or use progressive fallback
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                reply = llm_fallback.get_reply(session_id, fsm.state, message)
            else:
                fsm.increment_attempt()
                if fsm.should_offer_choice():
                    reply = content.get('strengths', {}).get('offer_choice', 
                        "I hear you, and sometimes it's hard to see our own strengths. Would you like to keep thinking about this, or shall we move on to talk about what's been on your mind?")
                elif fsm.should_force_advance():
                    fsm.save_response("Had difficulty articulating strengths")
                    fsm.next_step()
                    reply = f"{content['strengths']['acknowledge_move']} {content['worries']['prompt']}"
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
        elif intent == 'negation' and ('nothing' in normalized_message or 'no worries' in normalized_message or 'not worried' in normalized_message):
            # User explicitly says no worries - acknowledge and move on
            fsm.save_response("Nothing specific worrying me right now")
            fsm.next_step()
            reply = content['goals']['prompt']
        elif intent == 'affirmation' and fsm.get_attempt_count() > 0:
            # User chose to move on after being offered choice
            fsm.save_response("Preferred not to discuss worries in detail")
            fsm.next_step()
            reply = f"{content['worries']['acknowledge_move']} {content['goals']['prompt']}"
        elif confidence < 0.2 or intent == 'unclear':
            # Low confidence or unclear response - implement progressive fallback
            fsm.increment_attempt()
            if fsm.should_offer_choice():
                # First attempt failed - offer choice
                reply = content.get('worries', {}).get('offer_choice', 
                    "I understand if it's hard to talk about worries right now. Would you like to keep thinking about what's on your mind, or shall we move on to yarn about your goals instead?")
            elif fsm.should_force_advance():
                # Second attempt failed - acknowledge and move on
                fsm.save_response("Had difficulty articulating worries")
                fsm.next_step()
                reply = f"{content['worries']['acknowledge_move']} {content['goals']['prompt']}"
            else:
                # Initial clarification attempt
                reply = content.get('worries', {}).get('clarify', 
                    "What's been on your mind lately? Any concerns, stress, or challenges you're facing?")
        else:
            # Try LLM or use progressive fallback
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                reply = llm_fallback.get_reply(session_id, fsm.state, message)
            else:
                fsm.increment_attempt()
                if fsm.should_offer_choice():
                    reply = content.get('worries', {}).get('offer_choice', 
                        "I understand if it's hard to talk about worries right now. Would you like to keep thinking about what's on your mind, or shall we move on to yarn about your goals instead?")
                elif fsm.should_force_advance():
                    fsm.save_response("Had difficulty articulating worries")
                    fsm.next_step()
                    reply = f"{content['worries']['acknowledge_move']} {content['goals']['prompt']}"
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
        elif intent == 'affirmation' and fsm.get_attempt_count() > 0:
            # User chose to move on after being offered choice
            fsm.save_response("Preferred not to discuss goals in detail")
            fsm.next_step()
            # Create summary with all responses
            responses = fsm.get_all_responses()
            summary_text = create_summary(responses)
            reply = f"{content['goals']['acknowledge_move']} {content['summary']['prompt']}\n\n{summary_text}"
        elif intent == 'unclear' or confidence < 0.3:
            # Low confidence or unclear response - implement progressive fallback
            fsm.increment_attempt()
            if fsm.should_offer_choice():
                # First attempt failed - offer choice
                reply = content.get('goals', {}).get('offer_choice', 
                    "I can see thinking about goals might be challenging right now. Would you like to spend more time on this, or are you ready to hear what we've talked about today?")
            elif fsm.should_force_advance():
                # Second attempt failed - acknowledge and move on to summary
                fsm.save_response("Had difficulty articulating goals")
                fsm.next_step()
                # Create summary with all responses
                responses = fsm.get_all_responses()
                summary_text = create_summary(responses)
                reply = f"{content['goals']['acknowledge_move']} {content['summary']['prompt']}\n\n{summary_text}"
            else:
                # Initial clarification attempt
                reply = content.get('goals', {}).get('clarify', 
                    "What's one thing you'd like to work towards? It could be anything - big or small, short-term or long-term.")
        else:
            # Try LLM or use progressive fallback
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                reply = llm_fallback.get_reply(session_id, fsm.state, message)
            else:
                fsm.increment_attempt()
                if fsm.should_offer_choice():
                    reply = content.get('goals', {}).get('offer_choice', 
                        "I can see thinking about goals might be challenging right now. Would you like to spend more time on this, or are you ready to hear what we've talked about today?")
                elif fsm.should_force_advance():
                    fsm.save_response("Had difficulty articulating goals")
                    fsm.next_step()
                    # Create summary with all responses
                    responses = fsm.get_all_responses()
                    summary_text = create_summary(responses)
                    reply = f"{content['goals']['acknowledge_move']} {content['summary']['prompt']}\n\n{summary_text}"
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
