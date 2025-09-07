import os
import requests
import logging

logger = logging.getLogger(__name__)

# Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()  # "openai" or "ollama"
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "gpt-4")
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "45.0"))
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.8"))
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))
OPENAI_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

def call_llm_openai(system_prompt: str, user_message: str) -> str:
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
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
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"OpenAI error: {str(e)}")
        raise RuntimeError(f"LLM error: {str(e)}")

def call_llm_ollama(system_prompt: str, user_message: str) -> str:
    try:
        full_prompt = f"{system_prompt}\n\n{user_message}"
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
        return result.get("response", "").strip()
    except Exception as e:
        logger.error(f"Ollama error: {str(e)}")
        raise RuntimeError(f"LLM error: {str(e)}")

def call_llm(system_prompt: str, user_message: str) -> str:
    if LLM_PROVIDER == "ollama":
        return call_llm_ollama(system_prompt, user_message)
    return call_llm_openai(system_prompt, user_message)

# def is_llm_available() -> bool:
#     if LLM_PROVIDER == "ollama":
#         return True
#     return bool(API_KEY) and os.getenv("LLM_ENABLED", "false").lower() == "true"