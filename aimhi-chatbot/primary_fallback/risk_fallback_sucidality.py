import os
import logging
import time
from typing import Tuple, Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)

HF_TOKEN = os.getenv("HF_TOKEN")
HF_RISK_API_URL = os.getenv(
    "HF_RISK_API_URL",
    "https://router.huggingface.co/hf-inference/models/sentinet/suicidality",
)
CONFIDENCE_THRESHOLD = float(os.getenv("RISK_CONFIDENCE_THRESHOLD", 0.5))


def _normalize_risk_label(label: str) -> str:
    l = label.lower()
    if "suic" in l or l in {"label_1", "1", "positive"}:
        return "risk"
    return "no_risk"


def detect_risk_fallback(text: str) -> Tuple[str, float, Optional[str]]:
    start_time = time.time()
    try:
        if not HF_TOKEN:
            raise RuntimeError("HF_TOKEN not set; cannot call HF Inference API")
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs": text}
        resp = requests.post(HF_RISK_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        result: List[Dict[str, Any]] = resp.json()
        if not isinstance(result, list) or not result:
            raise RuntimeError("Empty risk response from HF API")

        # Choose the top-scoring label
        top = max(result, key=lambda r: float(r.get("score", 0.0)))
        label = _normalize_risk_label(str(top.get("label", "label_0")))
        confidence = float(top.get("score", 0.0))

        # Apply threshold only for promoting to risk
        if label == "risk" and confidence < CONFIDENCE_THRESHOLD:
            label = "no_risk"
            confidence = 1.0 - confidence

        logger.info(
            f"Risk: {label}, Confidence: {confidence:.2f}, Time: {time.time() - start_time:.3f}s"
        )
        return label, confidence, None
    except Exception as e:
        return "no_risk", 0.0, str(e)


def is_model_available() -> bool:
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN is not set; HF Inference API unavailable.")
    return True


def clear_model_cache():
    # No client-side cache to clear with requests-based approach
    logger.info("No HF cache to clear")
