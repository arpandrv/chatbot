"""
LLM Handoff Manager for personalized conversation continuation.
Integrates with summary_generator to provide comprehensive user context.
"""

import json
import asyncio
from typing import Dict, Optional, List
from database.repository import get_history
from llm.summary_generator import SummaryGenerator
from llm.client import LLMClient
from llm.guardrails import LLMGuardrails


class LLMHandoffManager:
    """Manages handoff from structured FSM to personalized LLM conversation."""
    
    def __init__(self):
        self.summary_generator = SummaryGenerator()
        self.llm_client = LLMClient(config_type="conversation")
        self.guardrails = LLMGuardrails()
        
    async def handle_llm_response(self, session_id: str, user_message: str) -> str:
        """
        Handle user message using comprehensive summary for personalized response.
        
        Args:
            session_id: User session ID
            user_message: Current user message
            
        Returns:
            LLM response with full context
        """
        try:
            # Get comprehensive summary (should be cached from FSM completion)
            summary_data = await self.summary_generator.generate_comprehensive_summary(session_id)
            comprehensive_summary = summary_data.get('comprehensive_summary', '')
            
            if not comprehensive_summary or summary_data.get('status') == 'fallback':
                # Fallback to basic response if no comprehensive summary
                return self._get_fallback_response(session_id, user_message)
            
            # Build system prompt with comprehensive context
            system_prompt = self._build_system_prompt(comprehensive_summary)
            
            # Get recent conversation context and combine with user message
            recent_context = self._get_recent_context(session_id)
            user_input = f"{recent_context}\n\nUser: {user_message}"
            
            # Apply pre-processing guardrails to user input
            processed_user_input = self.guardrails.pre_process(user_input)
            
            # Generate LLM response with proper system/user separation
            response = await self.llm_client.generate(
                system_prompt, 
                processed_user_input, 
                temperature=0.8
            )
            
            # Apply post-processing guardrails
            processed_response = self.guardrails.post_process(response)
            
            if processed_response and self.llm_client.validate_response(processed_response):
                return processed_response
            else:
                return self._get_fallback_response(session_id, user_message)
                
        except Exception as e:
            print(f"LLM handoff error: {e}")
            return self._get_fallback_response(session_id, user_message)
    
    def _build_system_prompt(self, comprehensive_summary: str) -> str:
        """Build system prompt using comprehensive user summary."""
        
        base_prompt = """You are Yarn, a supportive companion for young Aboriginal and Torres Strait Islander people. You just completed the Stay Strong 4-step conversation (support people, strengths, worries, goals) and now you're continuing with natural, personalized conversation.

IMPORTANT GUIDELINES:
- Be warm, supportive, and culturally respectful
- Use natural Aboriginal English terms when appropriate (deadly, mob, yarn, etc.)
- Never provide medical, clinical, or diagnostic advice
- Keep responses conversational, not therapeutic
- Reference their specific strengths, support people, and goals naturally
- Ask follow-up questions to keep the conversation flowing
- Celebrate their progress and encourage their goals

SAFETY RULES:
- If they mention crisis/risk situations, acknowledge supportively but direct to professional help
- Avoid clinical language or formal counseling techniques
- Keep responses under 100 words unless they ask for more detail
- Focus on being a caring friend who listens and encourages

"""
        
        user_context = f"""
COMPREHENSIVE USER PROFILE:
{comprehensive_summary}

Remember: This comprehensive analysis should guide your responses to be highly personalized and culturally appropriate. Reference specific details they shared to show you were listening and care about their unique situation.
"""
        
        return base_prompt + user_context
    
    def _get_recent_context(self, session_id: str, limit: int = 6) -> str:
        """Get recent conversation context for continuity."""
        history = get_history(session_id, limit)
        
        context = "RECENT CONVERSATION:\n"
        # Reverse to chronological order (get_history returns DESC)
        for row in reversed(history):
            role = "User" if row["role"] == "user" else "Yarn"
            # Truncate very long messages
            message = row["message"][:150] + "..." if len(row["message"]) > 150 else row["message"]
            context += f"{role}: {message}\n"
        
        return context
    
    def _get_fallback_response(self, session_id: str, user_message: str) -> str:
        """Provide fallback response when LLM is unavailable."""
        
        # Basic supportive responses based on message sentiment
        user_message_lower = user_message.lower()
        
        if any(word in user_message_lower for word in ['good', 'great', 'awesome', 'happy', 'excited']):
            return "That's deadly to hear! I'm really happy things are going well for you. What's been the best part?"
            
        elif any(word in user_message_lower for word in ['bad', 'sad', 'worried', 'stressed', 'difficult']):
            return "I hear you, and I'm here to listen. Remember the strengths you shared with me - you've got this. What's one small thing that might help right now?"
            
        elif any(word in user_message_lower for word in ['thanks', 'thank you', 'appreciate']):
            return "No worries at all, mate. I'm here whenever you need someone to yarn with. What's on your mind?"
            
        elif '?' in user_message:
            return "That's a great question. I'm here to listen and support you, though I can't give medical advice. What are your thoughts on it?"
            
        else:
            return "I hear you. Thanks for sharing that with me. How are you feeling about everything right now?"
    
    def should_use_llm_handoff(self, session_id: str) -> bool:
        """
        Check if LLM handoff should be used for this session.
        
        Args:
            session_id: User session ID
            
        Returns:
            Boolean indicating if LLM should handle the conversation
        """
        # Check if we have a comprehensive summary available
        try:
            # This is a quick check - in production you might cache this
            from core.session import get_session
            session = get_session(session_id)
            fsm = session['fsm']
            
            # Use LLM handoff if FSM is in summary state (conversation flow complete)
            return fsm.state == 'summary'
            
        except Exception:
            return False