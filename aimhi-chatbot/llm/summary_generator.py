"""
Simple summary generator for comprehensive user profiling.
Collects conversation data and generates LLM-based summaries for personalization.
"""

import json
from datetime import datetime
from typing import Dict, List
from core.session import get_session
from database.repository import get_history


class SummaryGenerator:
    """Generates comprehensive user summaries using LLM analysis."""
    
    async def generate_comprehensive_summary(self, session_id: str) -> Dict:
        """
        Generate comprehensive user summary using LLM for personalized conversation.
        
        Args:
            session_id: User session ID
            
        Returns:
            Dict containing comprehensive user summary and metadata
        """
        # Step 1: Collect all conversation messages
        conversation_messages = []
        history = get_history(session_id, limit=50)
        
        # Reverse to chronological order (get_history returns DESC)
        for row in reversed(history):
            # Handle sqlite3.Row objects properly
            role = row["role"] if row["role"] is not None else "unknown"
            message = row["message"] if row["message"] is not None else ""
            conversation_messages.append({
                "role": role,
                "message": message
            })
        
        # Step 2: Get FSM responses
        session = get_session(session_id)
        fsm_responses = session['fsm'].get_all_responses()
        
        # Step 3: Structure data for LLM analysis
        analysis_data = {
            "conversation_messages": conversation_messages,
            "stay_strong_responses": {
                "support_people": fsm_responses.get('support_people', 'Not provided'),
                "strengths": fsm_responses.get('strengths', 'Not provided'),
                "worries": fsm_responses.get('worries', 'Not provided'),
                "goals": fsm_responses.get('goals', 'Not provided')
            }
        }
        
        # Step 4: Generate comprehensive summary using LLM
        try:
            from llm.client import LLMClient
            llm_client = LLMClient(config_type="summary")
            
            system_prompt = self._build_system_prompt()
            user_data = self._format_user_data(analysis_data)
            
            comprehensive_summary = await llm_client.generate(system_prompt, user_data)
            
            return {
                "comprehensive_summary": comprehensive_summary,
                "session_id": session_id,
                "generation_timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            print(f"Comprehensive summary generation failed: {e}")
            return {
                "comprehensive_summary": self._create_fallback_summary(analysis_data),
                "session_id": session_id,
                "generation_timestamp": datetime.now().isoformat(),
                "status": "fallback",
                "error": str(e)
            }
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for comprehensive user analysis."""
        return """You are an expert psychological assistant specializing in Aboriginal and Torres Strait Islander youth mental health support. You work with the AIMhi Stay Strong therapeutic model which focuses on 4 key areas: Support People, Strengths, Worries, and Goals.

Your task is to analyze a complete conversation between a young Aboriginal/Torres Strait Islander person and an AI chatbot called "Yarn". Based on this conversation, create a comprehensive psychological and communication profile that will enable future AI systems to provide highly personalized, culturally appropriate support.

IMPORTANT CONTEXT ABOUT THE APP:
- This is the AIMhi-Y Supportive Yarn Chatbot implementing the Stay Strong 4-step model
- The conversation follows a structured flow: welcome → support_people → strengths → worries → goals → summary
- Users are Aboriginal and Torres Strait Islander youth seeking mental health support
- The chatbot uses culturally appropriate language (deadly, mob, yarn, etc.)
- Some users may give off-topic or unclear responses due to hesitation, cultural differences, or emotional state
- Some users may report having no support people, strengths, worries, or goals - handle these cases with cultural sensitivity

ANALYSIS REQUIREMENTS:
1. **Communication Style**: Analyze formality, cultural language use, openness level, verbosity
2. **Emotional State**: Assess overall emotional tone, coping mechanisms, resilience indicators  
3. **Cultural Context**: Note cultural language markers, connection to Aboriginal/Torres Strait Islander identity
4. **Support Network**: Evaluate family/community connections, isolation risk, relationship quality
5. **Personal Strengths**: Identify explicit and implicit strengths, confidence levels, growth areas
6. **Mental Health Indicators**: Assess worry levels, anxiety markers, protective factors
7. **Future Orientation**: Evaluate goal-setting ability, hope levels, motivation patterns
8. **Engagement Patterns**: Communication preferences, trust building, therapeutic alliance

HANDLE EDGE CASES:
- **Off-topic responses**: Look for underlying meanings, emotional deflection, or cultural communication styles
- **"No support"**: Assess isolation risk while recognizing cultural privacy norms and extended family concepts  
- **"No strengths"**: Identify implicit strengths in resilience, cultural identity, or survival skills
- **"No worries"**: Evaluate if this reflects genuine wellness, cultural stoicism, or avoidance
- **"No goals"**: Consider if this reflects present-focus, overwhelm, or cultural time concepts

OUTPUT FORMAT:
Provide a comprehensive narrative summary (400-600 words) that captures:
1. Overall psychological profile and cultural context
2. Communication preferences and engagement style  
3. Support network analysis and isolation risk assessment
4. Strength-based assessment with growth opportunities
5. Worry/stress analysis with coping mechanisms
6. Goal orientation and future planning capacity
7. Specific recommendations for personalized AI interaction

Write in a professional but warm tone that respects Aboriginal and Torres Strait Islander cultural perspectives. Focus on strengths while acknowledging challenges. This summary will be used by AI systems to provide culturally appropriate, personalized ongoing support."""

    def _format_user_data(self, analysis_data: Dict) -> str:
        """Format user data into structured prompt for LLM analysis."""
        
        # Format conversation messages
        conversation_text = "CONVERSATION TRANSCRIPT:\n"
        for msg in analysis_data["conversation_messages"]:
            conversation_text += f"{msg['role'].upper()}: {msg['message']}\n"
        
        # Format Stay Strong responses
        stay_strong_text = "\nSTAY STRONG 4-STEP RESPONSES:\n"
        for step, response in analysis_data["stay_strong_responses"].items():
            stay_strong_text += f"{step.replace('_', ' ').title()}: {response}\n"
        
        return f"{conversation_text}{stay_strong_text}\n\nPlease provide your comprehensive analysis:"
    
    def _create_fallback_summary(self, analysis_data: Dict) -> str:
        """Create fallback summary when LLM is unavailable."""
        
        stay_strong = analysis_data['stay_strong_responses']
        
        return f"""COMPREHENSIVE USER PROFILE (Generated via fallback method):

This user completed the Stay Strong 4-step conversation process. Here's their profile:

STAY STRONG RESPONSES:
- Support People: {stay_strong['support_people']}
- Strengths: {stay_strong['strengths']} 
- Worries: {stay_strong['worries']}
- Goals: {stay_strong['goals']}

CONVERSATION SUMMARY: The user engaged with {len(analysis_data['conversation_messages'])} total messages during the structured conversation flow.

RECOMMENDATIONS: Future interactions should build on the user's identified strengths while providing culturally appropriate support for their expressed concerns. Consider their support network and goals when personalizing responses."""