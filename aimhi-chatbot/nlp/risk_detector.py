import os
import json
import logging
from typing import Optional, Dict
import requests
from primary_fallback.risk_fallback_sucidality import detect_risk_fallback

logger = logging.getLogger(__name__)

# Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()  # "openai" or "ollama"
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "gpt-4")
RISK_TIMEOUT = float(os.getenv("LLM_TIMEOUT_RISK", "2.0"))
RISK_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE_RISK", "0.1"))
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "100"))
OPENAI_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

RISK_SYSTEM_PROMPT = os.getenv("LLM_SYSTEM_PROMPT_RISK")
if not RISK_SYSTEM_PROMPT:
    raise RuntimeError(
        "System prompt not specified. Please set the LLM_SYSTEM_PROMPT_RISK environment variable."
    )

def get_user_prompt(text: str) -> str:
    return f'Message: "{text}"'


def detect_risk_openai(text: str, timeout: Optional[float] = None) -> Dict:
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": RISK_SYSTEM_PROMPT},
                {"role": "user", "content": get_user_prompt(text)}
            ],
            "temperature": RISK_TEMPERATURE,
            "max_tokens": MAX_TOKENS
        }
        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout or RISK_TIMEOUT
        )
        response.raise_for_status()
        result = response.json()
        message = result["choices"][0]["message"]["content"].strip()
        return parse_json_response(message)
    except Exception as e:
        logger.error(f"OpenAI error: {str(e)}, falling back to local model")
        # Fallback to local HuggingFace model
        label, confidence, error = detect_risk_fallback(text)
        return {
            "label": label,
            "confidence": confidence,
            "method": "huggingface_fallback",
            "error": error or str(e)
        }


def detect_risk_ollama(text: str, timeout: Optional[float] = None) -> Dict:
    try:
        full_prompt = f"{RISK_SYSTEM_PROMPT}\n\n{get_user_prompt(text)}"
        payload = {
            "model": MODEL,
            "prompt": full_prompt,
            "temperature": RISK_TEMPERATURE,
            "stream": False
        }
        response = requests.post(
            f"{OLLAMA_API_BASE}/api/generate",
            json=payload,
            timeout=timeout or RISK_TIMEOUT
        )
        response.raise_for_status()
        result = response.json()
        message = result.get("response", "").strip()
        return parse_json_response(message)
    except Exception as e:
        logger.error(f"Ollama error: {str(e)}, falling back to local model")
        # Fallback to local HuggingFace model
        label, confidence, error = detect_risk_fallback(text)
        return {
            "label": label,
            "confidence": confidence,
            "method": "huggingface_fallback",
            "error": error or str(e)
        }


def parse_json_response(response_text: str) -> Dict:
    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, dict) and parsed.get("label") in {"risk", "no_risk"}:
            return parsed
        else:
            raise ValueError("Missing or invalid 'label' field")
    except Exception as e:
        logger.warning(f"Failed to parse response as JSON: {response_text} ({e})")
        return {"label": "no_risk", "error": f"Invalid format: {str(e)}"}


def detect_risk_llm(text: str, timeout: Optional[float] = None) -> Dict:
    """Detect risk using LLM with automatic fallback to local model."""
    if LLM_PROVIDER == "ollama":
        return detect_risk_ollama(text, timeout)
    return detect_risk_openai(text, timeout)


def is_llm_available() -> bool:
    """Check if LLM service is available."""
    if LLM_PROVIDER == "ollama":
        # Check if Ollama server is running
        try:
            response = requests.get(f"{OLLAMA_API_BASE}/api/tags", timeout=1.0)
            return response.status_code == 200
        except:
            return False
    return bool(API_KEY)


def detect_risk(text: str, timeout: Optional[float] = None) -> Dict:
    """Main risk detection with single-pass fallback.

    If an LLM is configured/available, return its result (including any
    internal fallback chosen by that path). Only use the direct HF fallback
    when no LLM is available.
    """
    if is_llm_available():
        # Return whatever the LLM path determines (LLM or its own fallback)
        return detect_risk_llm(text, timeout)

    # No LLM configured/available: use HF fallback directly
    logger.info("LLM not available, using HuggingFace fallback")
    label, confidence, error = detect_risk_fallback(text)
    return {
        "label": label,
        "confidence": confidence,
        "method": "huggingface_fallback",
        "error": error
    }
