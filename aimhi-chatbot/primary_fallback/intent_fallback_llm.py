"""
LLM-based Intent Classification Fallback
=========================================
Uses OpenAI or Ollama for intent classification when primary models fail.
Falls back to rule-based classification if LLM is unavailable.
"""

import os
import sys
import json
import logging
from typing import Dict, Optional
import requests

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# No secondary fallback - LLM only

logger = logging.getLogger(__name__)

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "gpt-4")
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "3.0"))
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "100"))
OPENAI_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

# Intent classification system prompt
SYSTEM_PROMPT = """You are an intent classifier for a mental health support chatbot.
Classify the user's message into exactly ONE of these categories:

- greeting: User is saying hello or starting conversation
- question: User is asking a question
- affirmative: User agrees, says yes, or confirms
- negative: User disagrees, says no, or denies
- support_people: User mentions people who support them (family, friends, counselors)
- strengths: User talks about their abilities, skills, or things they're good at
- worries: User mentions concerns, stress, anxiety, or problems
- goals: User talks about aspirations, plans, or things they want to achieve
- no_support: User explicitly says they have no support or nobody to help
- no_strengths: User explicitly says they have no strengths or aren't good at anything
- no_worries: User explicitly says they have no worries or concerns
- no_goals: User explicitly says they have no goals or plans
- unclear: Message is unclear, ambiguous, or doesn't fit other categories

Respond with JSON only: {"intent": "category_name"}
No explanations, just the JSON."""

def get_user_prompt(text: str) -> str:
    """Format user message for LLM."""
    return f'Classify this message: "{text}"'


def parse_intent_response(response_text: str) -> Dict:
    """Parse LLM response to extract intent."""
    try:
        # Try to parse as JSON
        parsed = json.loads(response_text.strip())
        if isinstance(parsed, dict) and "intent" in parsed:
            intent = parsed["intent"]
            # Validate intent is one of our categories
            valid_intents = [
                "greeting", "question", "affirmative", "negative",
                "support_people", "strengths", "worries", "goals",
                "no_support", "no_strengths", "no_worries", "no_goals", "unclear"
            ]
            if intent in valid_intents:
                return {"label": intent, "method": f"llm_{LLM_PROVIDER}"}
            else:
                logger.warning(f"Invalid intent from LLM: {intent}")
                return {"label": "unclear", "method": f"llm_{LLM_PROVIDER}_invalid"}
        else:
            raise ValueError("Missing 'intent' field in response")
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {response_text[:100]} - {e}")
        return {"label": None, "error": str(e)}


def classify_intent_openai(text: str) -> Dict:
    """Classify intent using OpenAI API."""
    try:
        if not API_KEY:
            logger.warning("OpenAI API key not configured")
            return {"label": None, "error": "No API key"}
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": get_user_prompt(text)}
            ],
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS
        }
        
        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()
        message = result["choices"][0]["message"]["content"].strip()
        return parse_intent_response(message)
        
    except requests.exceptions.Timeout:
        logger.error("OpenAI request timed out")
        return {"label": None, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenAI request failed: {e}")
        return {"label": None, "error": str(e)}
    except Exception as e:
        logger.error(f"OpenAI intent classification error: {e}")
        return {"label": None, "error": str(e)}


def classify_intent_ollama(text: str) -> Dict:
    """Classify intent using Ollama local LLM."""
    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\n{get_user_prompt(text)}"
        
        payload = {
            "model": MODEL,
            "prompt": full_prompt,
            "temperature": TEMPERATURE,
            "stream": False
        }
        
        response = requests.post(
            f"{OLLAMA_API_BASE}/api/generate",
            json=payload,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()
        message = result.get("response", "").strip()
        return parse_intent_response(message)
        
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out")
        return {"label": None, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama request failed: {e}")
        return {"label": None, "error": str(e)}
    except Exception as e:
        logger.error(f"Ollama intent classification error: {e}")
        return {"label": None, "error": str(e)}


def classify_intent_llm(text: str, current_step: Optional[str] = None) -> Dict:
    """
    Main function: Classify intent using LLM only.
    
    Args:
        text: User input text
        current_step: Current FSM step for context (unused without rule-based fallback)
    
    Returns:
        Dict with 'label' and 'method' keys
    """
    if not text or not text.strip():
        return {"label": "unclear", "method": "empty_input"}
    
    # Try LLM first
    logger.debug(f"Attempting LLM intent classification with {LLM_PROVIDER}")
    
    if LLM_PROVIDER == "ollama":
        result = classify_intent_ollama(text)
    else:
        result = classify_intent_openai(text)
    
    # Check if LLM succeeded
    if result.get("label") and not result.get("error"):
        logger.info(f"LLM classified intent as: {result['label']}")
        return result
    
    # LLM failed, return unclear
    logger.info(f"LLM failed ({result.get('error', 'unknown')}), returning unclear")
    return {
        "label": "unclear",
        "method": "llm_failed",
        "error": result.get("error", "unknown")
    }


# For testing independently
if __name__ == "__main__":
    test_messages = [
        "Hello there!",
        "My family supports me",
        "I'm good at playing football",
        "I'm worried about my exams",
        "I want to become a doctor",
        "I don't have anyone",
        "I'm not good at anything",
        "What do you mean?",
        "Yes, that's right",
        "No, I don't agree"
    ]
    
    print("Testing LLM Intent Classification with Fallback")
    print("=" * 50)
    
    for msg in test_messages:
        result = classify_intent_llm(msg)
        print(f"Message: '{msg}'")
        print(f"Result: {result}")
        print("-" * 30)