# aimhi-chatbot/llm/handoff_manager.py

"""
LLM Handoff Manager for personalized conversation continuation.
Manages the transition from structured FSM conversations to open-ended LLM interactions.
"""

import json
import logging
import os
from typing import Dict, Optional, List, Tuple
import time

from llm.client import LLMClient, LLMClientError, LLMTimeoutError, LLMValidationError
from llm.guardrails import LLMGuardrails

logger = logging.getLogger(__name__)


class HandoffError(Exception):
    """Base exception for handoff manager errors"""
    pass


class LLMHandoffManager:
    """
    Manages handoff from structured FSM to personalized LLM conversation.
    Provides both async and sync interfaces for compatibility.
    """
    
    def __init__(self):
        """Initialize the handoff manager with required components."""
        self.llm_client = None
        self.guardrails = LLMGuardrails()
        self.fallback_responses = self._load_fallback_responses()
        self.context_limit = 6  # Maximum conversation turns to include
        self.max_context_chars = 2000  # Maximum context string length
        
        # Initialize LLM client if available
        self._initialize_llm_client()
        
        logger.info(f"LLM Handoff Manager initialized. LLM available: {self.is_llm_available()}")

    def _initialize_llm_client(self) -> None:
        """Initialize LLM client with proper error handling."""
        try:
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                self.llm_client = LLMClient(config_type="conversation")
                logger.info("LLM client initialized successfully")
            else:
                logger.info("LLM is disabled via environment variable")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}. Will use fallback responses only.")
            self.llm_client = None

    def _load_fallback_responses(self) -> Dict[str, List[str]]:
        """Load configurable fallback responses."""
        return {
            "positive": [
                "That's deadly to hear! Thanks for sharing that with me.",
                "Good on ya! That sounds really positive.",
                "That's great! I'm glad to hear things are going well.",
                "Wonderful! That's something to feel proud about."
            ],
            "negative": [
                "I hear you, and that sounds really tough.",
                "Thanks for trusting me with that. It's okay to feel this way.",
                "That must be difficult to deal with. You're being really strong.",
                "I understand. It's normal to have these feelings sometimes."
            ],
            "neutral": [
                "Thanks for sharing that with me.",
                "I appreciate you telling me about this.",
                "That's interesting. Tell me more about that.",
                "I'm listening. What else is on your mind?"
            ],
            "question": [
                "That's a great question. What do you think about it?",
                "I hear your question. What are your thoughts on this?",
                "Good point to bring up. How do you feel about it?",
                "Thanks for asking. What's your take on this?"
            ],
            "gratitude": [
                "You're very welcome! I'm here whenever you need to chat.",
                "No worries at all, mate. That's what I'm here for.",
                "Happy to help! Feel free to keep talking about whatever's on your mind.",
                "My pleasure! How are you feeling about everything we've talked about?"
            ],
            "default": [
                "I hear what you're saying. Thanks for sharing that with me.",
                "That's worth thinking about. What else is on your mind?",
                "I appreciate you telling me this. How are you feeling about it?",
                "Thanks for opening up. Is there anything else you'd like to talk about?"
            ]
        }

    def is_llm_available(self) -> bool:
        """Check if LLM is available for use."""
        return self.llm_client is not None

    def handle_llm_response_sync(self, session_id: str, user_message: str) -> str:
        """
        **SYNC VERSION** - Handle user message using LLM with full context.
        This is the method called by the router.
        
        Args:
            session_id: User session ID
            user_message: Current user message
            
        Returns:
            LLM or fallback response
        """
        start_time = time.time()
        
        try:
            # Get conversation context
            context_summary = self._get_session_context(session_id)
            recent_messages = self._get_recent_messages(session_id)
            
            # If LLM is available, try to use it
            if self.is_llm_available():
                try:
                    response = self._generate_llm_response(
                        context_summary, 
                        recent_messages, 
                        user_message
                    )
                    
                    processing_time = int((time.time() - start_time) * 1000)
                    logger.info(f"LLM response generated in {processing_time}ms for session {session_id}")
                    
                    return response
                    
                except (LLMClientError, LLMTimeoutError, LLMValidationError) as e:
                    logger.warning(f"LLM generation failed for session {session_id}: {e}. Using fallback.")
                    # Fall through to fallback response
            
            # Use intelligent fallback
            fallback_response = self._get_intelligent_fallback(user_message)
            
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"Fallback response generated in {processing_time}ms for session {session_id}")
            
            return fallback_response
            
        except Exception as e:
            logger.error(f"Handoff manager error for session {session_id}: {e}", exc_info=True)
            return self._get_safe_fallback_response()

    async def handle_llm_response(self, session_id: str, user_message: str) -> str:
        """
        **ASYNC VERSION** - Kept for backward compatibility.
        Simply calls the sync version.
        """
        return self.handle_llm_response_sync(session_id, user_message)

    def _get_session_context(self, session_id: str) -> str:
        """
        Get session context safely without circular imports.
        
        Args:
            session_id: Session to get context for
            
        Returns:
            Context summary string
        """
        try:
            # Import here to avoid circular imports
            from core.session import get_session
            
            session = get_session(session_id)
            fsm = session.get('fsm')
            
            if not fsm:
                return "New conversation session."
            
            # Build context from FSM responses
            responses = fsm.get_all_responses()
            context_parts = []
            
            if responses.get('support_people'):
                context_parts.append(f"Support people: {responses['support_people']}")
            
            if responses.get('strengths'):
                context_parts.append(f"Strengths: {responses['strengths']}")
                
            if responses.get('worries'):
                context_parts.append(f"Worries: {responses['worries']}")
                
            if responses.get('goals'):
                context_parts.append(f"Goals: {responses['goals']}")
            
            if context_parts:
                context = "Previous conversation context: " + " | ".join(context_parts)
                # Truncate if too long
                if len(context) > self.max_context_chars:
                    context = context[:self.max_context_chars] + "..."
                return context
            else:
                return "User has completed the initial 4-step conversation."
                
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return "Continuing conversation from previous interaction."

    def _get_recent_messages(self, session_id: str, limit: int = None) -> List[Dict[str, str]]:
        """
        Get recent conversation messages safely.
        
        Args:
            session_id: Session to get messages for
            limit: Maximum number of messages (default: self.context_limit)
            
        Returns:
            List of recent messages
        """
        if limit is None:
            limit = self.context_limit
            
        try:
            # Import here to avoid circular imports
            from database.repository_v2 import get_history
            
            history = get_history(session_id, limit)
            messages = []
            
            # Convert database rows to dict format safely
            for row in reversed(history):  # get_history returns DESC, we want chronological
                try:
                    role = row["role"] if row and "role" in row else "unknown"
                    message = row["message"] if row and "message" in row else ""
                    
                    # Skip empty messages
                    if message and message.strip():
                        messages.append({
                            "role": role,
                            "message": message.strip()
                        })
                        
                except (KeyError, TypeError, AttributeError) as e:
                    logger.warning(f"Skipping malformed message row: {e}")
                    continue
            
            return messages[-limit:] if messages else []  # Keep only most recent
            
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []

    def _generate_llm_response(self, context_summary: str, recent_messages: List[Dict], user_message: str) -> str:
        """
        Generate response using LLM with context.
        
        Args:
            context_summary: Summary of session context
            recent_messages: Recent conversation messages
            user_message: Current user input
            
        Returns:
            Generated and validated response
        """
        # Build system prompt
        system_prompt = self._build_system_prompt(context_summary)
        
        # Build conversation history
        conversation_context = self._build_conversation_context(recent_messages, user_message)
        
        # Generate response
        response = self.llm_client.generate(system_prompt, conversation_context)
        
        # Apply guardrails
        filtered_response = self.guardrails.post_process(response)
        
        if not filtered_response:
            logger.warning("LLM response was filtered out by guardrails")
            raise LLMValidationError("Response failed guardrail filtering")
        
        return filtered_response

    def _build_system_prompt(self, context_summary: str) -> str:
        """Build system prompt with context."""
        base_prompt = """You are Yarn, a supportive companion for young Aboriginal and Torres Strait Islander people. You just completed the Stay Strong 4-step conversation and now you're continuing with natural, personalized conversation.

IMPORTANT GUIDELINES:
- Be warm, supportive, and culturally respectful
- Use natural Aboriginal English terms when appropriate (deadly, mob, yarn, etc.)
- Never provide medical, clinical, or diagnostic advice
- Keep responses conversational, not therapeutic
- Reference their specific context naturally in your responses
- Ask follow-up questions to keep the conversation flowing
- Stay under 100 words unless they ask for more detail

SAFETY RULES:
- If they mention crisis situations, acknowledge supportively but direct to professional help
- Focus on being a caring friend who listens and encourages
- Celebrate their progress and encourage their goals"""

        if context_summary:
            context_prompt = f"\n\nCONTEXT FROM PREVIOUS CONVERSATION:\n{context_summary}\n\nUse this context to provide personalized, relevant responses that show you remember what they shared."
            return base_prompt + context_prompt
        
        return base_prompt

    def _build_conversation_context(self, recent_messages: List[Dict], user_message: str) -> str:
        """Build conversation context for LLM."""
        if not recent_messages:
            return f"User: {user_message}"
        
        context_lines = []
        
        # Add recent messages (limit to avoid token overflow)
        for msg in recent_messages[-4:]:  # Only last 4 exchanges
            role = "User" if msg["role"] == "user" else "Yarn"
            message = msg["message"][:150] + "..." if len(msg["message"]) > 150 else msg["message"]
            context_lines.append(f"{role}: {message}")
        
        # Add current message
        context_lines.append(f"User: {user_message}")
        
        return "\n".join(context_lines)

    def _get_intelligent_fallback(self, user_message: str) -> str:
        """Get contextually appropriate fallback response."""
        message_lower = user_message.lower().strip()
        
        # Pattern matching for different response types
        if any(word in message_lower for word in ['thank', 'thanks', 'appreciate', 'grateful']):
            responses = self.fallback_responses["gratitude"]
        elif any(word in message_lower for word in ['good', 'great', 'awesome', 'happy', 'excited', 'deadly']):
            responses = self.fallback_responses["positive"]
        elif any(word in message_lower for word in ['bad', 'sad', 'worried', 'stressed', 'difficult', 'tough']):
            responses = self.fallback_responses["negative"]
        elif '?' in user_message:
            responses = self.fallback_responses["question"]
        else:
            responses = self.fallback_responses["neutral"]
        
        # Select response (could add more sophisticated selection)
        import random
        return random.choice(responses)

    def _get_safe_fallback_response(self) -> str:
        """Get a safe default response when everything else fails."""
        return "Thanks for sharing that with me. I'm here to listen and support you. What else is on your mind?"

    def should_use_llm_handoff(self, session_id: str) -> bool:
        """
        Check if LLM handoff should be used for this session.
        
        Args:
            session_id: User session ID
            
        Returns:
            Boolean indicating if LLM should handle the conversation
        """
        try:
            from core.session import get_session
            
            session = get_session(session_id)
            fsm = session.get('fsm')
            
            if not fsm:
                return False
            
            # Use LLM handoff if FSM is in summary state (conversation flow complete)
            return fsm.state == 'summary'
            
        except Exception as e:
            logger.error(f"Error checking LLM handoff conditions: {e}")
            return False

    def get_manager_info(self) -> Dict:
        """Get information about the handoff manager state."""
        return {
            "llm_available": self.is_llm_available(),
            "context_limit": self.context_limit,
            "max_context_chars": self.max_context_chars,
            "fallback_response_categories": list(self.fallback_responses.keys()),
            "llm_client_info": self.llm_client.get_client_info() if self.llm_client else None
        }


# Singleton instance for global use
_handoff_manager = None

def get_handoff_manager() -> LLMHandoffManager:
    """Get singleton handoff manager instance."""
    global _handoff_manager
    if _handoff_manager is None:
        _handoff_manager = LLMHandoffManager()
    return _handoff_manager


# Test function for development
def test_handoff_manager():
    """Test function for development and debugging."""
    try:
        manager = get_handoff_manager()
        print("✅ Handoff Manager initialized successfully")
        print(f"📋 Manager info: {manager.get_manager_info()}")
        
        # Test with a sample response
        test_session_id = "test-session-123"
        test_message = "Thank you for the conversation, that was really helpful!"
        
        response = manager.handle_llm_response_sync(test_session_id, test_message)
        print(f"🤖 Test response: {response}")
        
    except Exception as e:
        print(f"❌ Handoff Manager error: {e}")


if __name__ == "__main__":
    test_handoff_manager()