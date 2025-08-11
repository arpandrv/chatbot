"""
Varied response selector for natural conversation flow.
Selects appropriate responses from pools to avoid repetition.
"""

import json
import os
import random
from typing import Dict, List, Optional
from collections import defaultdict


class VariedResponseSelector:
    """Selects varied responses from pools to create natural conversation."""
    
    def __init__(self):
        """Initialize the response selector."""
        self.response_pools = self._load_response_pools()
        self.response_history = defaultdict(list)  # Track used responses per session
        self.max_history = 3  # Remember last 3 responses to avoid repetition
        
    def _load_response_pools(self) -> Dict:
        """Load response pools from JSON file."""
        config_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'config', 'response_pools.json'
        )
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: response_pools.json not found at {config_path}")
            return {}
    
    def get_response(self, category: str, subcategory: str, 
                    session_id: str = None, user_sentiment: str = None) -> str:
        """
        Get a varied response from the appropriate pool.
        
        Args:
            category: Main category (e.g., 'welcome', 'support_people')
            subcategory: Subcategory (e.g., 'greeting', 'acknowledgment')
            session_id: Session ID for tracking response history
            user_sentiment: User's emotional state for tone matching
            
        Returns:
            Selected response string
        """
        # Get the response pool
        if category not in self.response_pools:
            return self._get_fallback_response(category, subcategory)
        
        category_pools = self.response_pools[category]
        if subcategory not in category_pools:
            # Try to find a suitable alternative
            if 'acknowledgment' in category_pools:
                subcategory = 'acknowledgment'
            elif 'followup' in category_pools:
                subcategory = 'followup'
            else:
                return self._get_fallback_response(category, subcategory)
        
        response_pool = category_pools[subcategory]
        
        # Handle string or list response pools
        if isinstance(response_pool, str):
            return response_pool
        
        if not isinstance(response_pool, list) or not response_pool:
            return self._get_fallback_response(category, subcategory)
        
        # Filter out recently used responses if we have a session
        available_responses = response_pool.copy()
        if session_id:
            history_key = f"{session_id}_{category}_{subcategory}"
            used_responses = self.response_history.get(history_key, [])
            
            # Remove recently used responses from available pool
            available_responses = [r for r in available_responses if r not in used_responses]
            
            # If all responses have been used, reset and use all
            if not available_responses:
                available_responses = response_pool.copy()
                self.response_history[history_key] = []
        
        # Select response based on user sentiment if provided
        selected = self._select_by_sentiment(available_responses, user_sentiment)
        
        # Track the selected response
        if session_id:
            history_key = f"{session_id}_{category}_{subcategory}"
            self.response_history[history_key].append(selected)
            # Keep only recent history
            if len(self.response_history[history_key]) > self.max_history:
                self.response_history[history_key].pop(0)
        
        return selected
    
    def _select_by_sentiment(self, responses: List[str], sentiment: str = None) -> str:
        """Select response based on user sentiment for better tone matching."""
        if not sentiment or sentiment == 'neutral':
            return random.choice(responses)
        
        # Try to match tone (this is simplified - could be enhanced)
        if sentiment == 'positive':
            # Prefer enthusiastic responses
            enthusiastic_words = ['great', 'wonderful', 'excellent', 'deadly', 'brilliant']
            weighted_responses = []
            for response in responses:
                weight = 1
                for word in enthusiastic_words:
                    if word.lower() in response.lower():
                        weight = 3  # Triple the chance
                        break
                weighted_responses.extend([response] * weight)
            return random.choice(weighted_responses)
        
        elif sentiment == 'negative':
            # Prefer empathetic responses
            empathetic_words = ['understand', 'hear you', 'sorry', 'tough', 'difficult']
            weighted_responses = []
            for response in responses:
                weight = 1
                for word in empathetic_words:
                    if word.lower() in response.lower():
                        weight = 3  # Triple the chance
                        break
                weighted_responses.extend([response] * weight)
            return random.choice(weighted_responses)
        
        return random.choice(responses)
    
    def _get_fallback_response(self, category: str, subcategory: str) -> str:
        """Get a fallback response when pools aren't available."""
        fallbacks = {
            'welcome': "G'day! I'm here to have a supportive yarn with you. How are you feeling?",
            'support_people': "Tell me about the people who support you in your life.",
            'strengths': "What are some things you're good at or proud of?",
            'worries': "What's been on your mind lately?",
            'goals': "What's something you'd like to work towards?",
            'summary': "Thanks for sharing all of that with me today."
        }
        return fallbacks.get(category, "Let's continue our conversation.")
    
    def get_cultural_response(self, base_response: str, cultural_score: float) -> str:
        """
        Adjust response based on user's cultural language usage.
        
        Args:
            base_response: The base response text
            cultural_score: Score indicating how much cultural language user uses (0-1)
            
        Returns:
            Culturally adjusted response
        """
        if cultural_score < 0.3:
            # User doesn't use much cultural language, keep it standard
            return base_response
        
        # Add cultural phrases based on score
        cultural_additions = {
            0.3: ["mate"],
            0.5: ["deadly", "mob"],
            0.7: ["yarn", "deadly", "mob", "mate"]
        }
        
        # Find appropriate level
        level = 0.3
        for threshold in [0.7, 0.5, 0.3]:
            if cultural_score >= threshold:
                level = threshold
                break
        
        # Randomly add a cultural term if appropriate
        if random.random() < 0.5:  # 50% chance to add cultural flavor
            terms = cultural_additions[level]
            term = random.choice(terms)
            
            # Smart insertion based on term
            if term == "mate":
                if not any(word in base_response.lower() for word in ["mate", "friend"]):
                    base_response = base_response.replace("you", "you, mate", 1)
            elif term == "deadly":
                if "great" in base_response.lower():
                    base_response = base_response.replace("great", "deadly", 1)
                elif "good" in base_response.lower():
                    base_response = base_response.replace("good", "deadly", 1)
            elif term == "yarn":
                if "talk" in base_response.lower():
                    base_response = base_response.replace("talk", "yarn", 1)
                elif "chat" in base_response.lower():
                    base_response = base_response.replace("chat", "yarn", 1)
            elif term == "mob":
                if "people" in base_response.lower():
                    base_response = base_response.replace("people", "mob", 1)
                elif "family" in base_response.lower():
                    base_response = base_response.replace("family", "family mob", 1)
        
        return base_response
    
    def combine_responses(self, responses: List[str]) -> str:
        """
        Combine multiple response components into a natural flow.
        
        Args:
            responses: List of response components to combine
            
        Returns:
            Combined response string
        """
        # Filter out empty responses
        responses = [r for r in responses if r and r.strip()]
        
        if not responses:
            return ""
        
        # Join with appropriate spacing
        combined = " ".join(responses)
        
        # Clean up any double spaces or punctuation issues
        combined = " ".join(combined.split())  # Remove extra spaces
        combined = combined.replace(" .", ".")
        combined = combined.replace(" ?", "?")
        combined = combined.replace(" !", "!")
        combined = combined.replace(" ,", ",")
        
        return combined
    
    def clear_history(self, session_id: str = None):
        """Clear response history for a session or all sessions."""
        if session_id:
            # Clear specific session
            keys_to_remove = [k for k in self.response_history if k.startswith(session_id)]
            for key in keys_to_remove:
                del self.response_history[key]
        else:
            # Clear all history
            self.response_history.clear()