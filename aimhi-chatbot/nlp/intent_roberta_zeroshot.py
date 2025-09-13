"""
Zero-Shot Intent Classification via Hugging Face Inference API (requests)
AIMhi-Y Supportive Yarn Chatbot

Implements the approach described in hugdocs.md using direct HTTP calls.
"""

import os
import logging
from dotenv import load_dotenv
import re
from typing import Dict, Any, List, Tuple

import requests
from primary_fallback.intent_fallback_llm import classify_intent_llm

load_dotenv()

logger = logging.getLogger(__name__)

# --- Configuration ---
THRESHOLD = float(os.getenv("ROBERTA_INTENT_THRESHOLD", "0.3"))
HF_TOKEN = os.getenv("HF_TOKEN")
HF_ZS_API_URL = os.getenv(
    "HF_ZS_API_URL",
    "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli",
)

KEY_TO_PHRASE: Dict[str, str] = {
    "greeting": "saying hello or greeting",
    "question": "asking a question",
    "affirmative": "agreeing or saying yes",
    "negative": "disagreeing or saying no",
    "support_people": "talking about people who support me",
    "strengths": "talking about my strengths or abilities",
    "worries": "expressing worries or stress",
    "goals": "talking about goals or aspirations",
    "no_support": "saying I have no support",
    "no_strengths": "saying I have no strengths",
    "no_worries": "saying I have no worries",
    "no_goals": "saying I have no goals",
}

# Reverse mapping for decoding predictions back to internal keys
PHRASE_TO_KEY: Dict[str, str] = {v.lower(): k for k, v in KEY_TO_PHRASE.items()}


def preprocess_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    contractions = {"i'm": "i am", "don't": "do not", "can't": "cannot", "it's": "it is"}
    cultural_terms = {"mob": "family", "deadly": "good", "yarning": "talking"}
    for word, repl in {**contractions, **cultural_terms}.items():
        text = re.sub(rf"\b{word}\b", repl, text)
    return text.strip()
def _headers() -> Dict[str, str]:
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN is not set in environment. Set HF_TOKEN to call HF Inference API.")
    return {"Authorization": f"Bearer {HF_TOKEN}"}


def _zero_shot_request(text: str, candidate_labels: List[str]) -> Any:
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": candidate_labels,
            # Optional: provide a generic hypothesis template
            "hypothesis_template": "The intent is {}.",
            "multi_label": False,
        },
    }
    resp = requests.post(HF_ZS_API_URL, headers=_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


def _parse_zero_shot_response(result: Any) -> Tuple[str, float]:
    """Accept both classic zero-shot dict and list-of-dicts fallback."""
    # Typical zero-shot response: {"labels": [..], "scores": [..], ...}
    if isinstance(result, dict) and "labels" in result and "scores" in result:
        labels = result.get("labels", [])
        scores = result.get("scores", [])
        if labels and scores and len(labels) == len(scores):
            idx = int(max(range(len(scores)), key=lambda i: float(scores[i])))
            return str(labels[idx]), float(scores[idx])
    # Fallback: list of {label, score}
    if isinstance(result, list) and result:
        top = max(result, key=lambda r: float(r.get("score", 0.0)))
        return str(top.get("label", "unclear")), float(top.get("score", 0.0))
    # Unknown format
    return "unclear", 0.0


def classify_intent(text: str, threshold: float = THRESHOLD) -> Dict[str, Any]:
    if not text or not text.strip():
        return {"label": "unclear", "confidence": 0.0, "method": "empty_input"}

    text = preprocess_text(text)

    # Use zero-shot with human-readable phrases as candidate labels
    candidate_labels = list(KEY_TO_PHRASE.values())

    try:
        result = _zero_shot_request(text, candidate_labels)
        label_phrase, confidence = _parse_zero_shot_response(result)
    except Exception as e:
        logger.error(f"HF zero-shot request failed: {e}")
        return classify_intent_with_fallback(text)
    if confidence < threshold:
        return classify_intent_with_fallback(text)
    internal_key = PHRASE_TO_KEY.get(str(label_phrase).strip().lower(), "unclear")
    return {"label": internal_key, "confidence": confidence, "method": "hf_zero_shot_bart_mnli"}


def classify_intent_with_fallback(text: str, current_step: str = None) -> Dict[str, Any]:
    try:
        result = classify_intent_llm(text, current_step)
        return {
            "label": result.get("label", "unclear"),
            "confidence": "NA for LLMs",
            "method": "llm_fallback",
            "fallback_reason": result.get("fallback_reason", "roberta_low_confidence"),
        }
    except Exception as fallback_error:
        logger.error(f"LLM intent classification failed: {fallback_error}")
        return {"label": "unclear", "confidence": 0.0, "method": "all_failed"}
