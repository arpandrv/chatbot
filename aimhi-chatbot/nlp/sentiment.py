import os
import logging
from typing import Dict, Any, List

import requests
from primary_fallback.sentiment_fallback_llm import analyze_sentiment_llm

logger = logging.getLogger(__name__)

HF_TOKEN = os.getenv("HF_TOKEN")
HF_SENTIMENT_API_URL = os.getenv(
    "HF_SENTIMENT_API_URL",
    "https://router.huggingface.co/hf-inference/models/cardiffnlp/twitter-roberta-base-sentiment",
)
SENTIMENT_CONFIDENCE_THRESHOLD = float(os.getenv("SENTIMENT_CONFIDENCE_THRESHOLD", 0.5))


def _normalize_sentiment_label(label: str) -> str:
    label_check = label.lower()
    if "neg" in label_check or label_check in {"label_0", "negative"}:
        return "negative"
    if "neu" in label_check or label_check in {"label_1", "neutral"}:
        return "neutral"
    if "pos" in label_check or label_check in {"label_2", "positive"}:
        return "positive"
    return label_check


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment using the Hugging Face Inference API with Twitter-RoBERTa sentiment.
    Returns: {'label': str, 'confidence': float, 'method': str}
    Falls back to LLM-based method only if API call fails.
    """
    text = text.strip()
    if not text:
        logger.debug("Sentiment analysis skipped: empty input.")
        return {"label": "neutral", "confidence": 0.0, "method": "empty_input"}

    try:
        if not HF_TOKEN:
            raise RuntimeError("HF_TOKEN not set; cannot call HF Inference API")
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs": text}
        resp = requests.post(HF_SENTIMENT_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        result: List[Dict[str, Any]] = resp.json()
        if not isinstance(result, list) or not result:
            raise RuntimeError("Empty sentiment response from HF API")

        # Select top label by score
        top = max(result, key=lambda r: float(r.get("score", 0.0)))
        label = _normalize_sentiment_label(str(top.get("label", "neutral")))
        confidence = float(top.get("score", 0.0))

        # Apply threshold: if pos/neg is weak, prefer neutral
        if label in {"positive", "negative"} and confidence < SENTIMENT_CONFIDENCE_THRESHOLD:
            adjusted = {
                "label": "neutral",
                "confidence": 1.0 - confidence,
                "method": "hf_text_classification_threshold_adjusted",
                "below_threshold": True,
            }
            return adjusted

        return {"label": label, "confidence": confidence, "method": "hf_text_classification"}

    except Exception as e:
        logger.error(f"Sentiment HF API failed: {e}", exc_info=True)
        result = analyze_sentiment_llm(text)
        return {
            "label": result.get("label", "neutral"),
            "confidence": "NA for LLMs",
            "method": "llm_fallback_on_error",
            "fallback_reason": str(e),
        }
