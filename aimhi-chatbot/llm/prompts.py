"""
Enhanced LLM prompts system with rich context building for natural conversations.
Integrates with UserProfileBuilder and LLMContextBuilder for personalized interactions.
"""

from llm.context_builder import LLMContextBuilder
from core.user_profile import UserProfileBuilder

# Legacy system prompt for fallback use
BASIC_SYSTEM_PROMPT = """You are Yarn, a supportive companion for young Aboriginal and Torres Strait Islander people. 
You help them explore their strengths using the Stay Strong approach.
Never provide medical advice. Keep responses brief and encouraging."""

STEP_PROMPTS = {
    "support_people": "Help the user identify supportive people in their life. Ask about family, friends, Elders, or community members.",
    "strengths": "Help the user recognize what they're good at and proud of.",
    "worries": "Listen supportively to their concerns without trying to solve them.",
    "goals": "Help them identify one achievable goal they'd like to work toward."
}

# Initialize enhanced components
profile_builder = UserProfileBuilder()
context_builder = LLMContextBuilder(profile_builder)

def build_enhanced_system_prompt(session_id: str) -> str:
    """
    Build comprehensive system prompt using user profile data.
    
    Args:
        session_id: User session ID
        
    Returns:
        Complete enhanced system prompt
    """
    return context_builder.build_system_prompt(session_id)

def build_conversation_starter(session_id: str) -> str:
    """
    Build natural conversation starter for LLM handoff.
    
    Args:
        session_id: User session ID
        
    Returns:
        Personalized conversation starter
    """
    return context_builder.build_conversation_starter(session_id)

def should_use_enhanced_llm(session_id: str) -> bool:
    """
    Check if enhanced LLM should be used for this session.
    
    Args:
        session_id: User session ID
        
    Returns:
        Boolean indicating if enhanced LLM should be used
    """
    return context_builder.should_handoff_to_llm(session_id)

def build_enhanced_prompt(session_id: str, user_message: str, conversation_history: list = None) -> str:
    """
    Build enhanced prompt for LLM with full context and user message.
    
    Args:
        session_id: User session ID
        user_message: Current user message
        conversation_history: Recent conversation history (optional)
        
    Returns:
        Complete prompt for LLM
    """
    # Get system prompt with user profile
    system_prompt = build_enhanced_system_prompt(session_id)
    
    # Get conversation context
    recent_context = context_builder.get_conversation_context(session_id)
    
    # Format conversation history if provided
    history_text = ""
    if conversation_history:
        history_text = "\nRECENT MESSAGES:\n"
        for msg in conversation_history[-4:]:  # Last 4 messages
            role = msg.get('role', 'unknown')
            content = msg.get('message', msg.get('content', ''))
            history_text += f"{role.title()}: {content}\n"
    
    # Build complete prompt
    full_prompt = f"{system_prompt}\n\n{recent_context}{history_text}\n\nUser: {user_message}\nAssistant: "

    return full_prompt

def format_history(history):
    """Legacy function for backward compatibility."""
    return "\n".join([f"{turn['role']}: {turn['message']}" for turn in history])

def build_prompt(step, history, user_msg):
    """Legacy function for basic LLM fallback."""
    return f"""
{BASIC_SYSTEM_PROMPT}

Current focus: {STEP_PROMPTS.get(step, "")}

Recent conversation:
{format_history(history[-6:])}

User: {user_msg}
Assistant: [Respond in 1-2 sentences, staying supportive and on-topic]
"""