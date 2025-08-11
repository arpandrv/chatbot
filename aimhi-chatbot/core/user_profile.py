"""
User profile builder for tracking communication style and building LLM context.
Analyzes user responses to create personalized conversation profiles.
"""

import re
from typing import Dict, List, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from core.session import get_session


@dataclass
class UserProfile:
    """User profile containing communication style and Stay Strong data."""
    
    # Communication style
    formality: str = "casual"  # casual, formal, mixed
    verbosity: str = "brief"  # brief, moderate, detailed
    cultural_markers: List[str] = field(default_factory=list)
    emotion_words: List[str] = field(default_factory=list)
    preferred_topics: List[str] = field(default_factory=list)
    
    # Stay Strong data
    support_people: Dict = field(default_factory=lambda: {
        "primary": [],
        "specific": [],
        "support_level": "unknown",
        "raw_response": ""
    })
    
    strengths: Dict = field(default_factory=lambda: {
        "activities": [],
        "personality": [],
        "confidence": "unknown",
        "raw_response": ""
    })
    
    worries: Dict = field(default_factory=lambda: {
        "categories": [],
        "severity": "unknown",
        "openness": "unknown",
        "raw_response": ""
    })
    
    goals: Dict = field(default_factory=lambda: {
        "timeframe": "unknown",
        "specificity": "unknown",
        "confidence": "unknown",
        "raw_response": ""
    })
    
    # Conversation preferences
    pace: str = "moderate"  # fast, moderate, slow
    depth: str = "surface"  # surface, moderate, deep
    privacy_level: str = "cautious"  # open, cautious, private
    support_seeking: str = "passive"  # active, passive, resistant
    
    # Tracking
    message_count: int = 0
    total_word_count: int = 0
    response_times: List[float] = field(default_factory=list)


class UserProfileBuilder:
    """Builds and maintains user profiles from conversation data."""
    
    def __init__(self):
        """Initialize the profile builder."""
        self.profiles = {}  # session_id -> UserProfile
        
        # Classification dictionaries
        self.cultural_markers = [
            'deadly', 'mob', 'yarn', 'blackfella', 'whitefella',
            'aunty', 'uncle', 'elder', 'nan', 'pop', 'bub', 'cuz'
        ]
        
        self.emotion_indicators = {
            'positive': ['happy', 'good', 'great', 'awesome', 'love', 'excited', 
                        'proud', 'confident', 'strong', 'deadly', 'brilliant'],
            'negative': ['sad', 'worried', 'scared', 'angry', 'stressed', 'anxious',
                        'down', 'depressed', 'upset', 'frustrated', 'tired'],
            'neutral': ['okay', 'fine', 'alright', 'normal', 'average']
        }
        
        self.topic_keywords = {
            'family': ['family', 'mum', 'dad', 'parents', 'siblings', 'brother', 'sister'],
            'friends': ['friends', 'mates', 'friendship', 'buddies'],
            'school': ['school', 'study', 'homework', 'teacher', 'class', 'university'],
            'work': ['work', 'job', 'career', 'employment', 'boss'],
            'health': ['health', 'sick', 'mental', 'physical', 'wellbeing'],
            'sport': ['sport', 'football', 'basketball', 'swimming', 'exercise'],
            'music': ['music', 'singing', 'guitar', 'drums', 'band'],
            'art': ['art', 'drawing', 'painting', 'creative']
        }
        
        self.support_categories = {
            'family': ['mum', 'mom', 'dad', 'family', 'parents', 'siblings', 
                      'brother', 'sister', 'cousin', 'aunt', 'uncle', 'nan', 'pop'],
            'friends': ['friends', 'mates', 'bestie', 'buddy'],
            'authority': ['teacher', 'counselor', 'therapist', 'doctor', 'elder'],
            'romantic': ['partner', 'boyfriend', 'girlfriend', 'husband', 'wife']
        }
        
        self.strength_categories = {
            'activities': ['sport', 'music', 'art', 'cooking', 'gaming', 'reading'],
            'personality': ['kind', 'funny', 'caring', 'smart', 'creative', 'strong', 
                          'loyal', 'honest', 'patient', 'brave']
        }
        
        self.worry_categories = {
            'school': ['school', 'homework', 'exams', 'grades', 'university'],
            'family': ['family', 'parents', 'home', 'siblings'],
            'relationships': ['friends', 'boyfriend', 'girlfriend', 'relationship'],
            'future': ['future', 'job', 'career', 'money', 'independence'],
            'health': ['health', 'mental', 'physical', 'anxiety', 'depression']
        }
    
    def get_profile(self, session_id: str) -> UserProfile:
        """Get or create user profile for session."""
        if session_id not in self.profiles:
            self.profiles[session_id] = UserProfile()
        return self.profiles[session_id]
    
    def update_profile(self, session_id: str, message: str, 
                      intent: str, confidence: float, fsm_state: str):
        """
        Update user profile based on new message and analysis.
        
        Args:
            session_id: User session ID
            message: User's message
            intent: Classified intent
            confidence: Intent confidence score
            fsm_state: Current FSM state
        """
        profile = self.get_profile(session_id)
        profile.message_count += 1
        profile.total_word_count += len(message.split())
        
        # Analyze communication style
        self._analyze_communication_style(profile, message)
        
        # Update Stay Strong data if in relevant state
        if fsm_state == 'support_people' and intent == 'support_people':
            self._analyze_support_people(profile, message)
        elif fsm_state == 'strengths' and intent == 'strengths':
            self._analyze_strengths(profile, message)
        elif fsm_state == 'worries' and intent == 'worries':
            self._analyze_worries(profile, message)
        elif fsm_state == 'goals' and intent == 'goals':
            self._analyze_goals(profile, message)
        
        # Update conversation preferences
        self._update_conversation_preferences(profile, message, intent, confidence)
    
    def _analyze_communication_style(self, profile: UserProfile, message: str):
        """Analyze and update communication style indicators."""
        message_lower = message.lower()
        
        # Check cultural markers
        for marker in self.cultural_markers:
            if marker in message_lower and marker not in profile.cultural_markers:
                profile.cultural_markers.append(marker)
        
        # Check emotion words
        for emotion_type, words in self.emotion_indicators.items():
            for word in words:
                if word in message_lower and word not in profile.emotion_words:
                    profile.emotion_words.append(word)
        
        # Check topics
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                if topic not in profile.preferred_topics:
                    profile.preferred_topics.append(topic)
        
        # Analyze formality
        informal_markers = ["i'm", "im", "dont", "wont", "cant", "yeah", "nah", "mate"]
        formal_markers = ["i am", "do not", "will not", "cannot", "yes", "no"]
        
        informal_count = sum(1 for marker in informal_markers if marker in message_lower)
        formal_count = sum(1 for marker in formal_markers if marker in message_lower)
        
        if informal_count > formal_count:
            profile.formality = "casual"
        elif formal_count > informal_count:
            profile.formality = "formal"
        else:
            profile.formality = "mixed"
        
        # Analyze verbosity
        word_count = len(message.split())
        if word_count <= 5:
            profile.verbosity = "brief"
        elif word_count <= 15:
            profile.verbosity = "moderate"
        else:
            profile.verbosity = "detailed"
    
    def _analyze_support_people(self, profile: UserProfile, message: str):
        """Analyze support people response."""
        message_lower = message.lower()
        profile.support_people["raw_response"] = message
        
        # Categorize support people
        for category, keywords in self.support_categories.items():
            if any(keyword in message_lower for keyword in keywords):
                if category not in profile.support_people["primary"]:
                    profile.support_people["primary"].append(category)
        
        # Extract specific mentions
        specific_people = []
        if 'mum' in message_lower or 'mom' in message_lower:
            specific_people.append('mum')
        if 'dad' in message_lower:
            specific_people.append('dad')
        if 'friends' in message_lower:
            specific_people.append('friends')
        
        profile.support_people["specific"] = specific_people
        
        # Assess support level
        if any(word in message_lower for word in ['no one', 'nobody', 'alone']):
            profile.support_people["support_level"] = "low"
        elif len(profile.support_people["primary"]) >= 2:
            profile.support_people["support_level"] = "high"
        else:
            profile.support_people["support_level"] = "moderate"
    
    def _analyze_strengths(self, profile: UserProfile, message: str):
        """Analyze strengths response."""
        message_lower = message.lower()
        profile.strengths["raw_response"] = message
        
        # Categorize strengths
        for category, keywords in self.strength_categories.items():
            for keyword in keywords:
                if keyword in message_lower:
                    if keyword not in profile.strengths[category]:
                        profile.strengths[category].append(keyword)
        
        # Assess confidence
        confident_indicators = ['proud', 'good at', 'really', 'very', 'love doing']
        hesitant_indicators = ['i guess', 'maybe', 'sort of', 'kind of', 'not sure']
        
        if any(indicator in message_lower for indicator in confident_indicators):
            profile.strengths["confidence"] = "confident"
        elif any(indicator in message_lower for indicator in hesitant_indicators):
            profile.strengths["confidence"] = "hesitant"
        else:
            profile.strengths["confidence"] = "moderate"
    
    def _analyze_worries(self, profile: UserProfile, message: str):
        """Analyze worries response."""
        message_lower = message.lower()
        profile.worries["raw_response"] = message
        
        # Categorize worries
        for category, keywords in self.worry_categories.items():
            if any(keyword in message_lower for keyword in keywords):
                if category not in profile.worries["categories"]:
                    profile.worries["categories"].append(category)
        
        # Assess severity
        severe_indicators = ['really', 'very', 'extremely', 'so much', 'constantly']
        mild_indicators = ['a bit', 'sometimes', 'occasionally', 'little']
        
        if any(indicator in message_lower for indicator in severe_indicators):
            profile.worries["severity"] = "high"
        elif any(indicator in message_lower for indicator in mild_indicators):
            profile.worries["severity"] = "mild"
        else:
            profile.worries["severity"] = "moderate"
        
        # Assess openness
        if len(message.split()) >= 10:
            profile.worries["openness"] = "open"
        elif any(word in message_lower for word in ["don't want", "private", "rather not"]):
            profile.worries["openness"] = "private"
        else:
            profile.worries["openness"] = "cautious"
    
    def _analyze_goals(self, profile: UserProfile, message: str):
        """Analyze goals response."""
        message_lower = message.lower()
        profile.goals["raw_response"] = message
        
        # Assess timeframe
        short_term_indicators = ['soon', 'this year', 'next few', 'quickly']
        long_term_indicators = ['someday', 'eventually', 'future', 'years']
        
        if any(indicator in message_lower for indicator in short_term_indicators):
            profile.goals["timeframe"] = "short_term"
        elif any(indicator in message_lower for indicator in long_term_indicators):
            profile.goals["timeframe"] = "long_term"
        else:
            profile.goals["timeframe"] = "moderate"
        
        # Assess specificity
        specific_indicators = ['want to', 'plan to', 'going to', 'will']
        if any(indicator in message_lower for indicator in specific_indicators):
            profile.goals["specificity"] = "specific"
        elif len(message.split()) >= 8:
            profile.goals["specificity"] = "detailed"
        else:
            profile.goals["specificity"] = "general"
        
        # Assess confidence
        confident_indicators = ['will', 'definitely', 'determined', 'excited']
        uncertain_indicators = ['maybe', 'hope', 'try', 'not sure']
        
        if any(indicator in message_lower for indicator in confident_indicators):
            profile.goals["confidence"] = "determined"
        elif any(indicator in message_lower for indicator in uncertain_indicators):
            profile.goals["confidence"] = "uncertain"
        else:
            profile.goals["confidence"] = "hopeful"
    
    def _update_conversation_preferences(self, profile: UserProfile, 
                                        message: str, intent: str, confidence: float):
        """Update conversation preferences based on interaction patterns."""
        # Update privacy level
        if confidence > 0.8 and len(message.split()) >= 10:
            profile.privacy_level = "open"
        elif confidence < 0.4 or any(word in message.lower() for word in 
                                    ["private", "don't want", "rather not"]):
            profile.privacy_level = "private"
        else:
            profile.privacy_level = "cautious"
        
        # Update support seeking behavior
        if intent in ['support_people', 'worries'] and confidence > 0.7:
            profile.support_seeking = "active"
        elif intent == 'negation' or confidence < 0.3:
            profile.support_seeking = "resistant"
        else:
            profile.support_seeking = "passive"
        
        # Update conversation depth preference
        avg_words = profile.total_word_count / profile.message_count if profile.message_count else 0
        if avg_words >= 15:
            profile.depth = "deep"
        elif avg_words >= 8:
            profile.depth = "moderate"
        else:
            profile.depth = "surface"
    
    def is_ready_for_llm_handoff(self, session_id: str) -> bool:
        """Check if user profile is ready for LLM handoff."""
        session = get_session(session_id)
        fsm = session['fsm']
        
        # Must have completed all Stay Strong steps
        if not fsm.is_summary():
            return False
        
        profile = self.get_profile(session_id)
        responses = fsm.get_all_responses()
        
        # Check data completeness
        completed_responses = sum(1 for response in responses.values() if response)
        if completed_responses < 3:  # At least 3 out of 4 responses
            return False
        
        # Check engagement level
        if profile.message_count < 4:  # Minimum interaction
            return False
        
        # Check if user shows willingness to continue
        if profile.support_seeking == "resistant":
            return False
        
        return True
    
    def get_cultural_score(self, session_id: str) -> float:
        """Get cultural language usage score for response selection."""
        profile = self.get_profile(session_id)
        
        if not profile.total_word_count:
            return 0.0
        
        # Score based on cultural markers used
        marker_count = len(profile.cultural_markers)
        max_possible = min(marker_count, 3)  # Cap at 3 for scoring
        
        return min(max_possible / 3.0, 1.0)
    
    def get_profile_summary(self, session_id: str) -> Dict:
        """Get comprehensive profile summary for LLM context building."""
        profile = self.get_profile(session_id)
        session = get_session(session_id)
        responses = session['fsm'].get_all_responses()
        
        return {
            'communication_style': {
                'formality': profile.formality,
                'verbosity': profile.verbosity,
                'cultural_markers': profile.cultural_markers,
                'emotion_words': profile.emotion_words,
                'preferred_topics': profile.preferred_topics
            },
            'stay_strong_data': {
                'support_people': profile.support_people,
                'strengths': profile.strengths,
                'worries': profile.worries,
                'goals': profile.goals
            },
            'conversation_preferences': {
                'pace': profile.pace,
                'depth': profile.depth,
                'privacy_level': profile.privacy_level,
                'support_seeking': profile.support_seeking
            },
            'raw_responses': responses,
            'stats': {
                'message_count': profile.message_count,
                'avg_words_per_message': profile.total_word_count / profile.message_count if profile.message_count else 0
            }
        }
    
    def clear_profile(self, session_id: str):
        """Clear profile data for a session."""
        if session_id in self.profiles:
            del self.profiles[session_id]