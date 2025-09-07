"""
LLM-based Sentiment Analysis Fallback
======================================
Uses OpenAI or Ollama for sentiment analysis when primary models fail.
Falls back to keyword-based analysis if LLM is unavailable.
"""

import os
import sys
import json
import logging
from typing import Dict
import requests

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# No secondary fallback - LLM only

logger = logging.getLogger(__name__)

# LLM Configuration (reuse environment variables)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "gpt-4")
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "3.0"))
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "100"))
OPENAI_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

# Sentiment analysis system prompt
SYSTEM_PROMPT = """You are a sentiment analyzer for a mental health support chatbot.
Analyze the emotional tone of the user's message.

Classify the sentiment as exactly ONE of:
- positive: Message expresses positive emotions, happiness, hope, gratitude, excitement
- negative: Message expresses negative emotions, sadness, worry, anger, frustration, fear
- neutral: Message is factual, unclear, or has mixed/no clear emotional tone

Consider:
- Emotional words and phrases
- Overall tone and context
- Cultural expressions (e.g., "deadly" can mean "good" in Aboriginal English)

Respond with JSON only: {"sentiment": "positive" OR "negative" OR "neutral"}
No explanations, just the JSON."""

def get_user_prompt(text: str) -> str:
    """Format user message for LLM."""
    return f'Analyze the sentiment of: "{text}"'


def parse_sentiment_response(response_text: str) -> Dict:
    """Parse LLM response to extract sentiment."""
    try:
        # Try to parse as JSON
        parsed = json.loads(response_text.strip())
        if isinstance(parsed, dict) and "sentiment" in parsed:
            sentiment = parsed["sentiment"].lower()
            # Validate sentiment is one of our categories
            if sentiment in ["positive", "negative", "neutral"]:
                return {"label": sentiment, "method": f"llm_{LLM_PROVIDER}"}
            else:
                logger.warning(f"Invalid sentiment from LLM: {sentiment}")
                return {"label": "neutral", "method": f"llm_{LLM_PROVIDER}_invalid"}
        else:
            raise ValueError("Missing 'sentiment' field in response")
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {response_text[:100]} - {e}")
        return {"label": None, "error": str(e)}


def analyze_sentiment_openai(text: str) -> Dict:
    """Analyze sentiment using OpenAI API."""
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
        return parse_sentiment_response(message)
        
    except requests.exceptions.Timeout:
        logger.error("OpenAI request timed out")
        return {"label": None, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenAI request failed: {e}")
        return {"label": None, "error": str(e)}
    except Exception as e:
        logger.error(f"OpenAI sentiment analysis error: {e}")
        return {"label": None, "error": str(e)}


def analyze_sentiment_ollama(text: str) -> Dict:
    """Analyze sentiment using Ollama local LLM."""
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
        return parse_sentiment_response(message)
        
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out")
        return {"label": None, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama request failed: {e}")
        return {"label": None, "error": str(e)}
    except Exception as e:
        logger.error(f"Ollama sentiment analysis error: {e}")
        return {"label": None, "error": str(e)}


def analyze_sentiment_llm(text: str) -> Dict:
    """
    Main function: Analyze sentiment using LLM only.
    
    Args:
        text: User input text
    
    Returns:
        Dict with 'label' and 'method' keys
    """
    if not text or not text.strip():
        return {"label": "neutral", "method": "empty_input"}
    
    # Try LLM first
    logger.debug(f"Attempting LLM sentiment analysis with {LLM_PROVIDER}")
    
    if LLM_PROVIDER == "ollama":
        result = analyze_sentiment_ollama(text)
    else:
        result = analyze_sentiment_openai(text)
    
    # Check if LLM succeeded
    if result.get("label") and not result.get("error"):
        logger.info(f"LLM analyzed sentiment as: {result['label']}")
        return result
    
    # LLM failed, return neutral
    logger.info(f"LLM failed ({result.get('error', 'unknown')}), returning neutral")
    return {
        "label": "neutral",
        "method": "llm_failed",
        "error": result.get("error", "unknown")
    }


# For testing independently
if __name__ == "__main__":
    test_messages = [
        "I'm feeling great today!",
        "This is terrible, I hate everything",
        "The weather is cloudy",
        "I'm so happy and excited!",
        "I'm worried and stressed about exams",
        "My family lives in Sydney",
        "That's deadly mate!",  # Aboriginal English for "good"
        "I don't know what to say",
        "Everything is going wrong",
        "Thanks for your help"
    ]
    
    print("Testing LLM Sentiment Analysis with Fallback")
    print("=" * 50)
    
    for msg in test_messages:
        result = analyze_sentiment_llm(msg)
        print(f"Message: '{msg}'")
        print(f"Result: {result}")
        print("-" * 30)