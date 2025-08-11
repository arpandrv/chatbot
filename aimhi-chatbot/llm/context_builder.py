"""
LLM context builder for creating rich prompts from user profiles and Stay Strong data.
Builds comprehensive context for natural, personalized LLM conversations.
"""

from typing import Dict, Any
from core.user_profile import UserProfileBuilder
from core.session import get_session


class LLMContextBuilder:
    """Builds rich context for LLM conversations from user profile data."""
    
    def __init__(self, profile_builder: UserProfileBuilder):
        """Initialize context builder with profile builder reference."""
        self.profile_builder = profile_builder
        
    def build_system_prompt(self, session_id: str) -> str:
        """
        Build comprehensive system prompt for LLM handoff.
        
        Args:
            session_id: User session ID
            
        Returns:
            Complete system prompt string
        """
        profile_summary = self.profile_builder.get_profile_summary(session_id)
        
        # Core identity and guidelines
        base_prompt = """You are Yarn, a supportive companion for young Aboriginal and Torres Strait Islander people.

CORE IDENTITY:
- Culturally aware and respectful
- Uses natural Aboriginal English when appropriate  
- Warm, supportive, non-judgmental
- Focuses on strengths-based conversation
- Never provides medical/clinical advice

IMPORTANT SAFETY RULES:
- NEVER provide medical, clinical, or diagnostic advice
- If user mentions crisis/risk, redirect to professional help
- Keep responses conversational, not therapeutic
- Avoid clinical language or formal counseling techniques

"""
        
        # Add user-specific context
        user_context = self._build_user_context(profile_summary)
        
        # Conversation guidelines based on user profile
        guidelines = self._build_conversation_guidelines(profile_summary)
        
        # Response style recommendations
        style_guide = self._build_style_guide(profile_summary)
        
        # Combine all parts
        full_prompt = base_prompt + user_context + guidelines + style_guide
        
        return full_prompt
    
    def _build_user_context(self, profile_summary: Dict) -> str:
        """Build user-specific context section."""
        context = "\nCOMPREHENSIVE USER PROFILE:\n\n"
        
        # Communication style
        comm_style = profile_summary.get('communication_style', {})
        context += f"COMMUNICATION STYLE:\n"
        context += f"- Preferred formality: {comm_style.get('formality', 'casual')}\n"
        context += f"- Communication style: {comm_style.get('verbosity', 'brief')}\n"
        
        cultural_markers = comm_style.get('cultural_markers', [])
        if cultural_markers:
            context += f"- Cultural language used: {', '.join(cultural_markers[:3])}\n"
        
        emotion_words = comm_style.get('emotion_words', [])
        if emotion_words:
            context += f"- Emotional expressions: {', '.join(emotion_words[:3])}\n"
        
        topics = comm_style.get('preferred_topics', [])
        if topics:
            context += f"- Topics they engage with: {', '.join(topics[:3])}\n"
        
        # Stay Strong summary
        context += "\nSTAY STRONG SUMMARY:\n"
        stay_strong = profile_summary.get('stay_strong_data', {})
        
        # Support people
        support = stay_strong.get('support_people', {})
        if support.get('raw_response'):
            context += f"- Support People: {support['raw_response'][:100]}\n"
            if support.get('primary'):
                context += f"  Main types: {', '.join(support['primary'])}\n"
            context += f"  Support level: {support.get('support_level', 'unknown')}\n"
        
        # Strengths
        strengths = stay_strong.get('strengths', {})
        if strengths.get('raw_response'):
            context += f"- Personal Strengths: {strengths['raw_response'][:100]}\n"
            activities = strengths.get('activities', [])
            personality = strengths.get('personality', [])
            if activities or personality:
                all_strengths = activities + personality
                context += f"  Key strengths: {', '.join(all_strengths[:3])}\n"
            context += f"  Confidence level: {strengths.get('confidence', 'unknown')}\n"
        
        # Worries
        worries = stay_strong.get('worries', {})
        if worries.get('raw_response'):
            context += f"- Current Worries: {worries['raw_response'][:100]}\n"
            categories = worries.get('categories', [])
            if categories:
                context += f"  Main concerns: {', '.join(categories)}\n"
            context += f"  Openness level: {worries.get('openness', 'unknown')}\n"
        
        # Goals
        goals = stay_strong.get('goals', {})
        if goals.get('raw_response'):
            context += f"- Future Goals: {goals['raw_response'][:100]}\n"
            context += f"  Timeframe: {goals.get('timeframe', 'unknown')}\n"
            context += f"  Goal clarity: {goals.get('specificity', 'unknown')}\n"
        
        return context
    
    def _build_conversation_guidelines(self, profile_summary: Dict) -> str:
        """Build conversation guidelines based on user profile."""
        guidelines = "\nCONVERSATION GUIDELINES:\n"
        
        prefs = profile_summary.get('conversation_preferences', {})
        comm_style = profile_summary.get('communication_style', {})
        
        guidelines += "1. NATURAL FLOW: Continue the conversation naturally from the Stay Strong discussion\n"
        
        # Cultural language guidance
        cultural_markers = comm_style.get('cultural_markers', [])
        if cultural_markers:
            guidelines += f"2. CULTURAL LANGUAGE: Use terms like '{', '.join(cultural_markers[:2])}' naturally as they do\n"
        else:
            guidelines += "2. CULTURAL LANGUAGE: Keep language respectful but don't force cultural terms\n"
        
        # Personal connection
        guidelines += "3. PERSONAL CONNECTION: Reference their specific strengths, support people, and goals\n"
        
        # Tone guidance based on privacy level
        privacy_level = prefs.get('privacy_level', 'cautious')
        if privacy_level == 'open':
            guidelines += "4. SUPPORTIVE TONE: They're comfortable sharing - engage warmly and openly\n"
        elif privacy_level == 'private':
            guidelines += "4. SUPPORTIVE TONE: Respect their privacy - be gentle and don't push for details\n"
        else:
            guidelines += "4. SUPPORTIVE TONE: Be encouraging but respect their pace - they're somewhat cautious\n"
        
        guidelines += "5. AVOID: Medical advice, clinical language, formal counseling techniques\n"
        guidelines += "6. ENCOURAGE: Their identified strengths and support networks\n"
        
        return guidelines
    
    def _build_style_guide(self, profile_summary: Dict) -> str:
        """Build response style guide based on user preferences."""
        style_guide = "\nRESPONSE STYLE:\n"
        
        comm_style = profile_summary.get('communication_style', {})
        prefs = profile_summary.get('conversation_preferences', {})
        
        # Formality matching
        formality = comm_style.get('formality', 'casual')
        if formality == 'casual':
            style_guide += "- Match their casual communication style - use contractions, relaxed language\n"
        elif formality == 'formal':
            style_guide += "- Match their more formal communication style - avoid too much slang\n"
        else:
            style_guide += "- Use a balanced mix of casual and respectful language\n"
        
        # Length guidance
        verbosity = comm_style.get('verbosity', 'brief')
        if verbosity == 'brief':
            style_guide += "- Keep responses concise - they prefer brief exchanges\n"
        elif verbosity == 'detailed':
            style_guide += "- They like detailed conversations - you can elaborate more\n"
        else:
            style_guide += "- Use moderate-length responses - not too brief, not too long\n"
        
        # Engagement style
        support_seeking = prefs.get('support_seeking', 'passive')
        if support_seeking == 'active':
            style_guide += "- They actively seek support - feel free to offer guidance and ask follow-up questions\n"
        elif support_seeking == 'resistant':
            style_guide += "- They may resist help - be very gentle and focus on listening rather than advising\n"
        else:
            style_guide += "- They're open but not pushy - balance listening with gentle encouragement\n"
        
        style_guide += "- Ask follow-up questions about their interests and goals\n"
        style_guide += "- Celebrate their strengths and progress regularly\n"
        style_guide += "- Reference their support people as resources when appropriate\n"
        
        style_guide += "\nRemember: This is a yarn (conversation) between friends, not a clinical session.\n"
        style_guide += "Focus on being a supportive companion who genuinely cares about their wellbeing.\n"
        
        return style_guide
    
    def build_conversation_starter(self, session_id: str) -> str:
        """
        Build a natural conversation starter for LLM handoff.
        
        Args:
            session_id: User session ID
            
        Returns:
            Conversation starter message
        """
        profile_summary = self.profile_builder.get_profile_summary(session_id)
        stay_strong = profile_summary.get('stay_strong_data', {})
        
        # Extract key elements for personalized starter
        support_people = stay_strong.get('support_people', {}).get('raw_response', '')
        strengths = stay_strong.get('strengths', {}).get('raw_response', '')
        worries = stay_strong.get('worries', {}).get('raw_response', '')
        goals = stay_strong.get('goals', {}).get('raw_response', '')
        
        # Build personalized starter based on what they shared
        starter_elements = []
        
        if strengths:
            # Reference their strengths
            starter_elements.append(f"I love hearing about your strengths - {strengths[:30]}...")
        
        if goals:
            # Reference their goals
            starter_elements.append(f"Your goal about {goals[:30]}... sounds really meaningful")
        
        if worries and len(worries.strip()) > 10:
            # Acknowledge their worries if they shared substantial concerns
            starter_elements.append("thanks for trusting me with what's been on your mind")
        
        # Create natural transition
        if starter_elements:
            starter = f"Thanks for sharing all that with me. {' and '.join(starter_elements)}. "
        else:
            starter = "Thanks for having that yarn with me. "
        
        # Add continuation prompt
        continuation_options = [
            "What's been the best part of your week so far?",
            "How have you been feeling about things lately?", 
            "What's something you're looking forward to?",
            "Tell me more about what's been going well for you.",
            "What's been keeping you busy these days?"
        ]
        
        # Choose based on their sharing style
        privacy_level = profile_summary.get('conversation_preferences', {}).get('privacy_level', 'cautious')
        if privacy_level == 'open':
            continuation = continuation_options[0]  # More specific
        elif privacy_level == 'private':
            continuation = continuation_options[4]  # General
        else:
            continuation = continuation_options[2]  # Positive focus
        
        return starter + continuation
    
    def should_handoff_to_llm(self, session_id: str) -> bool:
        """
        Check if conversation is ready for LLM handoff.
        
        Args:
            session_id: User session ID
            
        Returns:
            Boolean indicating if ready for handoff
        """
        return self.profile_builder.is_ready_for_llm_handoff(session_id)
    
    def get_conversation_context(self, session_id: str, last_messages: int = 3) -> str:
        """
        Get recent conversation context for LLM continuation.
        
        Args:
            session_id: User session ID
            last_messages: Number of recent messages to include
            
        Returns:
            Formatted conversation context
        """
        # This would integrate with the database to get recent messages
        # For now, return a simple context based on FSM state
        session = get_session(session_id)
        fsm = session['fsm']
        responses = fsm.get_all_responses()
        
        context = "RECENT CONVERSATION CONTEXT:\n"
        context += "Just completed the Stay Strong discussion covering:\n"
        
        if responses.get('support_people'):
            context += f"- Support people: {responses['support_people'][:60]}...\n"
        
        if responses.get('strengths'):
            context += f"- Strengths: {responses['strengths'][:60]}...\n"
        
        if responses.get('worries'):
            context += f"- Worries: {responses['worries'][:60]}...\n"
        
        if responses.get('goals'):
            context += f"- Goals: {responses['goals'][:60]}...\n"
        
        context += "\nNow transitioning to open conversation. User is ready to continue chatting.\n"
        
        return context