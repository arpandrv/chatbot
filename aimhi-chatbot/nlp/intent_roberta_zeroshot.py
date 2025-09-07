"""
RoBERTa Zero-Shot Intent Classification Module (Functional + LRU Version)
AIMhi-Y Supportive Yarn Chatbot

Lightweight version using lru_cache for model loading and no singleton class.
"""

import os
import logging
from dotenv import load_dotenv
import re
from typing import Tuple, Dict, Any, List
from pathlib import Path
from functools import lru_cache

import numpy as np
from transformers import AutoTokenizer
import onnxruntime as ort
from primary_fallback.intent_fallback_llm import classify_intent_llm

load_dotenv()

logger = logging.getLogger(__name__)

# --- Configuration ---
THRESHOLD = float(os.getenv("ROBERTA_INTENT_THRESHOLD", "0.3"))
MODEL_PATH = Path(os.getenv("ROBERTA_MODEL_PATH", "ai_models/roberta-large-mnli"))
ONNX_MODEL_PATH = MODEL_PATH / "onnx" / "model_int8.onnx"

INTENT_TEMPLATES: Dict[str, List[str]] = {
    'greeting': ["This is a greeting or hello", "The user is saying hello"],
    'question': ["This is a question", "The user is asking something"],
    'affirmative': ["The user agrees or says yes", "This is a positive response"],
    'negative': ["The user disagrees or says no", "This is a negative response"],
    'support_people': ["The user is talking about people who support them", "This mentions family or friends who help"],
    'strengths': ["The user is talking about their strengths or abilities", "This mentions things they are good at"],
    'worries': ["The user is talking about worries or concerns", "This mentions stress or anxiety"],
    'goals': ["The user is talking about goals or aspirations", "This mentions future plans or dreams"],
    'no_support': ["The user says they have no support", "The user mentions having nobody to help them"],
    'no_strengths': ["The user says they have no strengths", "The user mentions not being good at anything"],
    'no_worries': ["The user says they have no worries", "The user mentions not being concerned about anything"],
    'no_goals': ["The user says they have no goals", "The user mentions not having plans or dreams"],
    'unclear': ["This message is unclear or confusing", "The meaning is ambiguous"]
}

@lru_cache()
def load_roberta_model() -> Tuple[Any, Any]:
    if not ONNX_MODEL_PATH.exists():
        logger.error(f"ONNX model not found at {ONNX_MODEL_PATH}")
        raise FileNotFoundError(f"ONNX model not found at {ONNX_MODEL_PATH}")

    logger.info(f"Loading ONNX model from {ONNX_MODEL_PATH}")
    session_options = ort.SessionOptions()
    session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(str(ONNX_MODEL_PATH), session_options, providers=['CPUExecutionProvider'])
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH), use_fast=True)
    return session, tokenizer

def preprocess_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    contractions = {"i'm": "i am", "don't": "do not", "can't": "cannot", "it's": "it is"}
    cultural_terms = {"mob": "family", "deadly": "good", "yarning": "talking"}
    for word, repl in {**contractions, **cultural_terms}.items():
        text = re.sub(rf'\b{word}\b', repl, text)
    return text.strip()

def compute_entailment_score(text: str, hypothesis: str) -> float:
    try:
        session, tokenizer = load_roberta_model()
        inputs = tokenizer(text, hypothesis, truncation=True, padding='max_length', max_length=256, return_tensors='np')
        ort_inputs = {k: v.astype(np.int64) for k, v in inputs.items()}
        logits = session.run(None, ort_inputs)[0][0]
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        return float(probs[2])  # Entailment score
    except Exception as e:
        logger.error(f"Entailment error for '{text[:20]}...': {e}")
        return 0.0


def classify_intent(text: str, threshold: float = THRESHOLD) -> Dict[str, Any]:
    if not text or not text.strip():
        return {'label': 'unclear', 'confidence': 0.0, 'method': 'empty_input'}

    text = preprocess_text(text)

    scores = {}
    for intent, templates in INTENT_TEMPLATES.items():
        if intent == 'unclear':
            continue
        max_score = max((compute_entailment_score(text, hyp) for hyp in templates), default=0.0)
        scores[intent] = max_score

    if not scores:
        return {'label': 'unclear', 'confidence': 0.0, 'method': 'no_scores'}

    best_intent, confidence = max(scores.items(), key=lambda item: item[1])
    if confidence < threshold:
        return classify_intent_with_fallback(text)
    return {'label': best_intent, 'confidence': confidence, 'method': 'roberta_zero_shot'}


def classify_intent_with_fallback(text: str, current_step: str = None) -> Dict[str, Any]:
    try:
        result = classify_intent_llm(text, current_step)
        return {
            'label': result.get('label', 'unclear'), 
            'confidence': 'NA for LLMs', 
            'method': 'llm_fallback',
            'fallback_reason': result.get('fallback_reason', 'roberta_low_confidence')
        }
    except Exception as fallback_error:
        logger.error(f"LLM intent classification failed: {fallback_error}")
        return {'label': 'unclear', 'confidence': 0.0, 'method': 'all_failed'}
