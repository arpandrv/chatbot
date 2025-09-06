import os
import logging
import time
from typing import Tuple, Optional
from functools import lru_cache
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import warnings

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

MODEL_NAME = os.getenv("HF_MODEL_NAME", "sentinetyd/suicidality")  # corrected name
CACHE_DIR = os.getenv("HF_CACHE_DIR", os.path.join(os.path.dirname(__file__), "..", "models", "sentinet_suicidality"))
MAX_LENGTH = int(os.getenv("HF_MAX_LENGTH", 512))
CONFIDENCE_THRESHOLD = float(os.getenv("HF_CONFIDENCE_THRESHOLD", 0.5))

@lru_cache(maxsize=1)
def load_model_and_tokenizer():
    os.makedirs(CACHE_DIR, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return model.to(device), tokenizer

def detect_risk_fallback(text: str) -> Tuple[str, float, Optional[str]]:
    start_time = time.time()
    try:
        model, tokenizer = load_model_and_tokenizer()
        inputs = tokenizer(text, truncation=True, max_length=MAX_LENGTH, return_tensors="pt")
        device = model.device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)[0]

            # Use model config for label mapping
            id2label = getattr(model.config, "id2label", {0: "LABEL_0", 1: "LABEL_1"})
            idx_non = [k for k, v in id2label.items() if v.upper() == "LABEL_0"][0]
            idx_sui = [k for k, v in id2label.items() if v.upper() == "LABEL_1"][0]

            prob_no_risk = probs[idx_non].item()
            prob_risk = probs[idx_sui].item()

        label = "risk" if prob_risk > CONFIDENCE_THRESHOLD else "no_risk"
        confidence = prob_risk if label == "risk" else prob_no_risk
        logger.info(f"Risk: {label}, Confidence: {confidence:.2f}, Time: {time.time() - start_time:.3f}s")
        return label, confidence, None
    except Exception as e:
        return "no_risk", 0.0, str(e)


def is_model_available() -> bool:
    try:
        load_model_and_tokenizer()
        return True
    except Exception as e:
        raise RuntimeError(f"Model is not available: {str(e)}") from e

def clear_model_cache():
    load_model_and_tokenizer.cache_clear()
    logger.info("Cleared model cache")