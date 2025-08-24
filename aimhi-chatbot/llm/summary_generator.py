# aimhi-chatbot/llm/summary_generator.py

"""
Simple session summary generator for the AIMhi-Y Supportive Yarn Chatbot.
Creates concise summaries of user conversations for context and personalization.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import time

from llm.client import LLMClient, LLMClientError, LLMTimeoutError, LLMValidationError

logger = logging.getLogger(__name__)


class SummaryGeneratorError(Exception):
    """Base exception for summary generator errors"""
    pass


class SummaryGenerator:
    """
    Generates session summaries using LLM analysis or rule-based fallback.
    Focused on simplicity and reliability for prototype use.
    """
    
    def __init__(self):
        """Initialize the summary generator."""
        self.llm_client = None
        self.max_conversation_length = 50  # Maximum messages to analyze
        self.max_prompt_chars = 1500  # Maximum prompt length
        self.summary_cache = {}  # Simple in-memory cache
        
        # Initialize LLM client if available
        self._initialize_llm_client()
        
        logger.info(f"Summary Generator initialized. LLM available: {self.is_llm_available()}")

    def _initialize_llm_client(self) -> None:
        """Initialize LLM client with proper error handling."""
        try:
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                self.llm_client = LLMClient(config_type="summary")
                logger.info("LLM client initialized for summary generation")
            else:
                logger.info("LLM is disabled, using rule-based summaries only")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client for summaries: {e}")
            self.llm_client = None

    def is_llm_available(self) -> bool:
        """Check if LLM is available for summary generation."""
        return self.llm_client is not None

    def generate_session_summary(self, session_id: str, summary_type: str = 'complete') -> Dict[str, Any]:
        """
        Generate a session summary using LLM or rule-based approach.
        
        Args:
            session_id: Session to summarize
            summary_type: Type of summary ('partial', 'complete', 'context')
            
        Returns:
            Dictionary containing summary data and metadata
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"{session_id}_{summary_type}"
            if cache_key in self.summary_cache:
                cached_summary = self.summary_cache[cache_key]
                if self._is_cache_valid(cached_summary):
                    logger.debug(f"Using cached summary for session {session_id}")
                    return cached_summary
            
            # Collect session data
            session_data = self._collect_session_data(session_id)
            
            if not session_data:
                return self._create_empty_summary(session_id, summary_type)
            
            # Generate summary
            if self.is_llm_available() and summary_type in ['complete', 'context']:
                try:
                    summary = self._generate_llm_summary(session_data, summary_type)
                    logger.info(f"LLM summary generated for session {session_id}")
                except (LLMClientError, LLMTimeoutError, LLMValidationError) as e:
                    logger.warning(f"LLM summary failed: {e}. Using rule-based fallback.")
                    summary = self._generate_rule_based_summary(session_data, summary_type)
            else:
                summary = self._generate_rule_based_summary(session_data, summary_type)
            
            # Create final summary object
            summary_result = {
                'summary': summary,
                'session_id': session_id,
                'summary_type': summary_type,
                'generation_timestamp': datetime.now().isoformat(),
                'generation_time_ms': int((time.time() - start_time) * 1000),
                'status': 'success',
                'method': 'llm' if self.is_llm_available() else 'rule_based'
            }
            
            # Cache the result
            self.summary_cache[cache_key] = summary_result
            
            return summary_result
            
        except Exception as e:
            logger.error(f"Summary generation failed for session {session_id}: {e}", exc_info=True)
            return self._create_error_summary(session_id, summary_type, str(e))

    def _collect_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Safely collect session data without circular imports.
        
        Args:
            session_id: Session to collect data for
            
        Returns:
            Dictionary with session data or None if unavailable
        """
        try:
            session_data = {
                'fsm_responses': {},
                'conversation_messages': [],
                'session_info': {}
            }
            
            # Get FSM responses safely
            try:
                from core.session import get_session
                session = get_session(session_id)
                fsm = session.get('fsm')
                
                if fsm:
                    session_data['fsm_responses'] = fsm.get_all_responses()
                    session_data['session_info'] = {
                        'current_state': fsm.state,
                        'session_id': session_id
                    }
                    
            except Exception as e:
                logger.warning(f"Could not get FSM data: {e}")
            
            # Get conversation messages safely
            try:
                from database.repository_v2 import get_history
                history = get_history(session_id, self.max_conversation_length)
                
                for row in reversed(history):  # Convert to chronological order
                    if row and 'role' in row and 'message' in row:
                        role = str(row['role']) if row['role'] else 'unknown'
                        message = str(row['message']) if row['message'] else ''
                        
                        if message.strip():  # Only include non-empty messages
                            session_data['conversation_messages'].append({
                                'role': role,
                                'message': message.strip()
                            })
                            
            except Exception as e:
                logger.warning(f"Could not get conversation history: {e}")
            
            # Return data only if we have something useful
            if session_data['fsm_responses'] or session_data['conversation_messages']:
                return session_data
            else:
                logger.info(f"No substantial session data found for {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error collecting session data: {e}")
            return None

    def _generate_llm_summary(self, session_data: Dict[str, Any], summary_type: str) -> str:
        """Generate summary using LLM."""
        system_prompt = self._build_system_prompt(summary_type)
        user_prompt = self._format_session_data(session_data)
        
        # Ensure prompt isn't too long
        if len(user_prompt) > self.max_prompt_chars:
            user_prompt = user_prompt[:self.max_prompt_chars] + "\n[Data truncated for length]"
        
        response = self.llm_client.generate(system_prompt, user_prompt)
        
        return response.strip()

    def _build_system_prompt(self, summary_type: str) -> str:
        """Build appropriate system prompt for summary type."""
        base_prompt = """You are creating a session summary for a supportive conversation with a young Aboriginal or Torres Strait Islander person using the AIMhi Stay Strong 4-step model.

IMPORTANT GUIDELINES:
- Be respectful and culturally appropriate
- Focus on strengths and positive aspects
- Keep summary concise and factual
- Use respectful, non-clinical language
- Protect privacy - no specific personal details

"""
        
        if summary_type == 'complete':
            return base_prompt + """Create a complete session summary covering:
1. Support people mentioned
2. Strengths identified  
3. Worries or concerns discussed
4. Goals or aspirations shared
5. Overall conversation tone

Keep it under 200 words and focus on the positive aspects."""

        elif summary_type == 'context':
            return base_prompt + """Create a brief context summary for continuing this conversation:
- Key topics discussed
- User's communication style
- Important details to remember
- Appropriate tone for future responses

Keep it under 150 words."""

        else:  # partial
            return base_prompt + """Create a brief summary of the conversation so far:
- Main topics covered
- User's current needs
- Progress through the 4-step model

Keep it under 100 words."""

    def _format_session_data(self, session_data: Dict[str, Any]) -> str:
        """Format session data for LLM analysis."""
        prompt_parts = []
        
        # Add FSM responses
        fsm_responses = session_data.get('fsm_responses', {})
        if fsm_responses:
            prompt_parts.append("STAY STRONG 4-STEP RESPONSES:")
            for step, response in fsm_responses.items():
                if response and response.strip():
                    step_name = step.replace('_', ' ').title()
                    prompt_parts.append(f"{step_name}: {response}")
        
        # Add conversation messages (limited)
        messages = session_data.get('conversation_messages', [])
        if messages:
            prompt_parts.append("\nCONVERSATION SAMPLE:")
            # Include last 6 messages to keep prompt manageable
            for msg in messages[-6:]:
                role = msg['role'].title()
                message = msg['message'][:200] + "..." if len(msg['message']) > 200 else msg['message']
                prompt_parts.append(f"{role}: {message}")
        
        # Add session info
        session_info = session_data.get('session_info', {})
        if session_info.get('current_state'):
            prompt_parts.append(f"\nCurrent conversation state: {session_info['current_state']}")
        
        return "\n".join(prompt_parts)

    def _generate_rule_based_summary(self, session_data: Dict[str, Any], summary_type: str) -> str:
        """Generate summary using rule-based approach."""
        fsm_responses = session_data.get('fsm_responses', {})
        messages = session_data.get('conversation_messages', [])
        
        summary_parts = []
        
        # Analyze FSM responses
        if fsm_responses:
            summary_parts.append("SESSION SUMMARY:")
            
            if fsm_responses.get('support_people'):
                summary_parts.append(f"• Support Network: User identified their support people")
            
            if fsm_responses.get('strengths'):
                summary_parts.append(f"• Strengths: User shared their abilities and positive qualities")
            
            if fsm_responses.get('worries'):
                summary_parts.append(f"• Concerns: User discussed things on their mind")
            
            if fsm_responses.get('goals'):
                summary_parts.append(f"• Goals: User shared their aspirations")
        
        # Add conversation stats
        if messages:
            user_messages = len([m for m in messages if m['role'] == 'user'])
            summary_parts.append(f"• Conversation: {user_messages} user messages exchanged")
            
            # Simple sentiment analysis
            positive_words = ['good', 'great', 'happy', 'excited', 'proud', 'deadly']
            negative_words = ['worried', 'stressed', 'sad', 'difficult', 'tough']
            
            all_text = ' '.join([m['message'].lower() for m in messages if m['role'] == 'user'])
            positive_count = sum(1 for word in positive_words if word in all_text)
            negative_count = sum(1 for word in negative_words if word in all_text)
            
            if positive_count > negative_count:
                summary_parts.append("• Tone: Generally positive conversation")
            elif negative_count > positive_count:
                summary_parts.append("• Tone: User shared some challenges")
            else:
                summary_parts.append("• Tone: Balanced conversation")
        
        if not summary_parts:
            return "New conversation session with limited interaction so far."
        
        return '\n'.join(summary_parts)

    def _create_empty_summary(self, session_id: str, summary_type: str) -> Dict[str, Any]:
        """Create empty summary for sessions with no data."""
        return {
            'summary': "No conversation data available for this session.",
            'session_id': session_id,
            'summary_type': summary_type,
            'generation_timestamp': datetime.now().isoformat(),
            'status': 'empty',
            'method': 'none'
        }

    def _create_error_summary(self, session_id: str, summary_type: str, error: str) -> Dict[str, Any]:
        """Create error summary when generation fails."""
        return {
            'summary': "Summary generation encountered an error. Using basic session data.",
            'session_id': session_id,
            'summary_type': summary_type,
            'generation_timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': error,
            'method': 'error_fallback'
        }

    def _is_cache_valid(self, cached_summary: Dict[str, Any], max_age_minutes: int = 30) -> bool:
        """Check if cached summary is still valid."""
        try:
            from datetime import datetime, timedelta
            
            timestamp_str = cached_summary.get('generation_timestamp')
            if not timestamp_str:
                return False
            
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            age = datetime.now() - timestamp.replace(tzinfo=None)
            
            return age < timedelta(minutes=max_age_minutes)
            
        except Exception:
            return False

    def get_cached_summary(self, session_id: str, summary_type: str = 'complete') -> Optional[Dict[str, Any]]:
        """Get cached summary if available and valid."""
        cache_key = f"{session_id}_{summary_type}"
        cached = self.summary_cache.get(cache_key)
        
        if cached and self._is_cache_valid(cached):
            return cached
        
        return None

    def clear_cache(self, session_id: str = None) -> None:
        """Clear summary cache for a specific session or all sessions."""
        if session_id:
            keys_to_remove = [k for k in self.summary_cache.keys() if k.startswith(session_id)]
            for key in keys_to_remove:
                del self.summary_cache[key]
            logger.debug(f"Cleared cache for session {session_id}")
        else:
            self.summary_cache.clear()
            logger.debug("Cleared all summary cache")

    def get_generator_info(self) -> Dict[str, Any]:
        """Get information about the generator state."""
        return {
            'llm_available': self.is_llm_available(),
            'max_conversation_length': self.max_conversation_length,
            'max_prompt_chars': self.max_prompt_chars,
            'cached_summaries': len(self.summary_cache),
            'cache_keys': list(self.summary_cache.keys()),
            'llm_client_info': self.llm_client.get_client_info() if self.llm_client else None
        }


# Singleton instance for global use
_summary_generator = None

def get_summary_generator() -> SummaryGenerator:
    """Get singleton summary generator instance."""
    global _summary_generator
    if _summary_generator is None:
        _summary_generator = SummaryGenerator()
    return _summary_generator


# Convenience functions
def generate_session_summary(session_id: str, summary_type: str = 'complete') -> Dict[str, Any]:
    """Convenience function to generate a session summary."""
    generator = get_summary_generator()
    return generator.generate_session_summary(session_id, summary_type)


def get_session_context_summary(session_id: str) -> Optional[str]:
    """Get a brief context summary for LLM handoff."""
    try:
        generator = get_summary_generator()
        result = generator.generate_session_summary(session_id, 'context')
        return result.get('summary')
    except Exception as e:
        logger.error(f"Error getting context summary: {e}")
        return None


# Test function for development
def test_summary_generator():
    """Test function for development and debugging."""
    try:
        generator = get_summary_generator()
        print("✅ Summary Generator initialized successfully")
        print(f"📋 Generator info: {generator.get_generator_info()}")
        
        # Test with a dummy session
        test_session_id = "test-session-123"
        
        summary = generator.generate_session_summary(test_session_id, 'partial')
        print(f"📄 Test summary: {summary}")
        
    except Exception as e:
        print(f"❌ Summary Generator error: {e}")


if __name__ == "__main__":
    test_summary_generator()