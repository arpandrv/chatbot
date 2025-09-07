# chatbot/aimhi_chatbot/nlp/sentiment.py

import logging
from functools import lru_cache
from typing import Dict, Any, Tuple, List

import torch
import torch.nn.functional as F
from transformers import PreTrainedTokenizer, PreTrainedModel, AutoTokenizer, AutoModelForSequenceClassification, AutoConfig
import torch

import torch


from primary_fallback.sentiment_fallback_llm import analyze_sentiment_llm

logger = logging.getLogger(__name__)

MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"

@lru_cache()
def load_model_and_tokenizer() -> Tuple[PreTrainedTokenizer, PreTrainedModel, torch.device, List[str]]:
    """
    Loads the tokenizer, model, device, and sentiment labels for the Twitter-RoBERTa model.

    Returns:
        Tuple containing:
            - tokenizer: Hugging Face tokenizer
            - model: Pretrained PyTorch model
            - device: torch.device (cuda or cpu)
            - labels: List of sentiment labels (e.g., ["Negative", "Neutral", "Positive"])
    """
    logger.info(f"Loading sentiment model: {MODEL_NAME}")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.eval()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Load model config to retrieve correct label mapping
    config = AutoConfig.from_pretrained(MODEL_NAME)
    labels = [config.id2label[i] for i in range(len(config.id2label))]

    logger.info(f"Model loaded on device: {device} with labels: {labels}")
    return tokenizer, model, device, labels


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment using a cached Twitter-RoBERTa model.
    Returns: {'label': str, 'confidence': float, 'method': str}
    Falls back to keyword-based method only if model fails.
    """
    text = text.strip()
    if not text:
        logger.debug("Sentiment analysis skipped: empty input.")
        return {"label": "neutral", "confidence": 0.0, "method": "empty_input"}

    try:
        tokenizer, model, device, labels = load_model_and_tokenizer()
        inputs = tokenizer(
            text, return_tensors="pt", truncation=True, padding=True, max_length=512
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1).cpu().numpy()[0]

        idx = int(probs.argmax())
        label = labels[idx]
        confidence = float(probs[idx])
        return {"label": label.lower(), "confidence": confidence, "method": "twitter_roberta"}

    except Exception as e:
        logger.error(f"Sentiment model failed: {e}", exc_info=True)
        result = analyze_sentiment_llm(text)
        return {
            "label": result.get("label", "neutral"), 
            "confidence": "NA for LLMs", 
            "method": "llm_fallback_on_error",
            "fallback_reason": str(e)
        }