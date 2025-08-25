# Recommended file: aimhi-chatbot/nlp/intent_roberta_zeroshot.py

#!/usr/bin/env python3
"""
RoBERTa Zero-Shot Intent Classification Module
AIMhi-Y Supportive Yarn Chatbot

This module provides a RoBERTa-based zero-shot intent classifier using the
FacebookAI/roberta-large-mnli model for natural language inference.

Features:
- Thread-safe singleton pattern for reliable multi-threaded use.
- Zero-shot classification without model training.
- Context-aware confidence boosting based on the FSM's current state.
- Comprehensive text preprocessing pipeline with cultural context awareness.
- Optimized for inference speed using a local ONNX Runtime model.
- Robust model loading that searches multiple common paths.
"""

import os
import logging
import re
import time
import threading
import warnings
from typing import Tuple, Optional, Dict, Any, List
from pathlib import Path

# Suppress only specific known warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='transformers')
warnings.filterwarnings('ignore', message='.*resume_download.*', module='transformers')
warnings.filterwarnings('ignore', category=UserWarning, message='.*TypedStorage.*')

import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

# Gracefully import optional dependencies
try:
    from transformers import AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("`transformers` library not found. Please install with `pip install transformers`.")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("`onnxruntime` library not found. Please install with `pip install onnxruntime`.")


class RoBERTaZeroShotClassifier:
    """
    Thread-safe Singleton RoBERTa Zero-Shot Intent Classifier.

    Uses an ONNX-optimized roberta-large-mnli model for zero-shot classification
    of user intents through natural language inference (NLI).
    """
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    INTENT_TEMPLATES = {
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

    def __new__(cls):
        """Thread-safe singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(RoBERTaZeroShotClassifier, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initializes the classifier once using a thread-safe lock."""
        if RoBERTaZeroShotClassifier._initialized:
            return
        with self._lock:
            if RoBERTaZeroShotClassifier._initialized:
                return
            self._session = None
            self._tokenizer = None
            self._model_path = None
            self._is_available = False
            self._load_model()
            RoBERTaZeroShotClassifier._initialized = True

    def _get_model_path(self) -> Path:
        """Get model path with clear expectations."""
        
        # Single source of truth
        model_path = Path(os.getenv('ROBERTA_MODEL_PATH', 'ai_models/roberta-large-mnli'))
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"RoBERTa model not found at {model_path}. "
                f"Set ROBERTA_MODEL_PATH environment variable or ensure model is at default location."
            )
        
        return model_path

    def _load_model(self):
        """Loads the ONNX model and tokenizer with comprehensive error handling."""
        if not (TRANSFORMERS_AVAILABLE and ONNX_AVAILABLE):
            logger.error("Cannot load RoBERTa model due to missing libraries.")
            return

        try:
            model_dir = self._get_model_path()
        except FileNotFoundError as e:
            logger.error(str(e))
            return

        onnx_path = model_dir / 'onnx' / 'model_int8.onnx'
        if not onnx_path.exists():
            logger.warning(f"Optimized ONNX model not found at {onnx_path}. Searching for alternatives.")
            alt_path = next((p for p in (model_dir / 'onnx').glob('*.onnx') if p.is_file()), None)
            if not alt_path:
                logger.error(f"No ONNX model file found in {model_dir / 'onnx'}")
                return
            onnx_path = alt_path

        try:
            logger.info(f"Loading ONNX model from {onnx_path}")
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(str(onnx_path), session_options, providers=['CPUExecutionProvider'])
            self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir), use_fast=True)
            self._warmup_model()
            self._is_available = True
            self._model_path = model_dir
            logger.info("RoBERTa zero-shot model is ready for inference.")
        except Exception as e:
            logger.error(f"Failed to load RoBERTa model or tokenizer: {e}", exc_info=True)
            self._is_available = False

    def _warmup_model(self):
        """Warms up the model with a dummy inference call."""
        try:
            self._compute_entailment_score_onnx("warmup", "this is a test")
            logger.info("Model warmed up successfully.")
        except Exception as e:
            logger.warning(f"Model warmup failed (non-critical): {e}")

    def is_available(self) -> bool:
        """Checks if the model is loaded and ready for inference."""
        return self._is_available

    def _preprocess_text(self, text: str) -> str:
        """Preprocesses text for intent classification."""
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        contractions = {"i'm": "i am", "don't": "do not", "can't": "cannot", "it's": "it is"}
        cultural_terms = {"mob": "family", "deadly": "good", "yarning": "talking"}
        for word, replacement in {**contractions, **cultural_terms}.items():
            text = re.sub(rf'\b{word}\b', replacement, text)
        return text.strip()

    def _compute_entailment_score_onnx(self, text: str, hypothesis: str) -> float:
        """Computes the entailment score between a text and a hypothesis."""
        try:
            inputs = self._tokenizer(text, hypothesis, truncation=True, padding='max_length', max_length=256, return_tensors='np')
            ort_inputs = {k: v.astype(np.int64) for k, v in inputs.items()}
            logits = self._session.run(None, ort_inputs)[0][0]
            exp_logits = np.exp(logits - np.max(logits)) # Softmax with stability
            probs = exp_logits / np.sum(exp_logits)
            return float(probs[2]) # Return entailment probability
        except Exception as e:
            logger.error(f"Error computing entailment for text '{text[:20]}...': {e}")
            return 0.0

    def _apply_context_boosting(self, scores: Dict[str, float], current_step: Optional[str]) -> Dict[str, float]:
        """Boosts scores based on the current conversation step."""
        if not current_step:
            return scores
        boosted_scores = scores.copy()
        boost_factors = {
            'support_people': {'support_people': 1.5, 'no_support': 1.3},
            'strengths': {'strengths': 1.5, 'no_strengths': 1.3},
            'worries': {'worries': 1.5, 'no_worries': 1.3, 'negative': 1.2},
            'goals': {'goals': 1.5, 'no_goals': 1.3, 'affirmative': 1.1},
            'welcome': {'greeting': 1.4, 'question': 1.2},
        }
        if current_step in boost_factors:
            for intent, factor in boost_factors[current_step].items():
                if intent in boosted_scores:
                    boosted_scores[intent] = min(boosted_scores[intent] * factor, 1.0)
        return boosted_scores

    def classify(self, text: str, current_step: Optional[str] = None, threshold: float = 0.3) -> Tuple[str, float]:
        """Classifies user intent using the zero-shot model."""
        if not self.is_available() or not text.strip():
            return 'unclear', 0.0
        
        processed_text = self._preprocess_text(text)
        if not processed_text:
            return 'unclear', 0.0

        intent_scores = {}
        for intent, hypotheses in self.INTENT_TEMPLATES.items():
            if intent == 'unclear': continue
            scores = [self._compute_entailment_score_onnx(processed_text, h) for h in hypotheses]
            intent_scores[intent] = float(np.max(scores)) if scores else 0.0

        boosted_scores = self._apply_context_boosting(intent_scores, current_step)
        
        if not boosted_scores:
            return 'unclear', 0.0
        
        best_intent, confidence = max(boosted_scores.items(), key=lambda item: item[1])

        if confidence < threshold:
            return 'unclear', confidence
        
        return best_intent, confidence

# --- Public API Functions ---

_roberta_classifier_instance = RoBERTaZeroShotClassifier()

def is_roberta_available() -> bool:
    """Checks if the RoBERTa model is loaded and available for use."""
    return _roberta_classifier_instance.is_available()

def get_roberta_info() -> Dict[str, Any]:
    """Returns information about the loaded RoBERTa model."""
    if not is_roberta_available():
        return {'available': False, 'error': 'Model not loaded or required libraries are missing.'}
    return {
        'available': True,
        'model_type': 'RoBERTa-large-MNLI (Zero-Shot via ONNX)',
        'model_path': str(_roberta_classifier_instance._model_path or 'Unknown'),
        'num_classes': len(_roberta_classifier_instance.INTENT_TEMPLATES),
    }

def classify_intent(text: str, current_step: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple, predictable intent classification with single fallback path.
    Priority order: RoBERTa → Rule-based → Unclear
    """
    if not text or not text.strip():
        return {'label': 'unclear', 'confidence': 0.0, 'method': 'empty_input'}
    
    # Priority order: use the first available classifier
    classifiers = [
        ('roberta_zero_shot', _try_roberta_classify),
        ('rule_based', _try_rule_classify),
    ]
    
    for method, classifier_func in classifiers:
        try:
            result = classifier_func(text, current_step)
            result['method'] = method
            # Apply intent mapping before returning
            intent_mapping = {'affirmative': 'affirmation', 'negative': 'negation'}
            result['label'] = intent_mapping.get(result['label'], result['label'])
            return result
        except Exception as e:
            logger.warning(f"Classifier {method} failed: {e}")
            continue
    
    # All classifiers failed
    return {'label': 'unclear', 'confidence': 0.0, 'method': 'all_failed'}


def _try_roberta_classify(text: str, current_step: Optional[str]) -> Dict[str, Any]:
    """Try RoBERTa classification - raises exception if not available."""
    if not is_roberta_available():
        raise RuntimeError("RoBERTa not available")
    
    intent, confidence = _roberta_classifier_instance.classify(text, current_step)
    return {'label': intent, 'confidence': confidence}


def _try_rule_classify(text: str, current_step: Optional[str]) -> Dict[str, Any]:
    """Try rule-based classification - should always work."""
    from fallbacks.rule_based_intent import classify_intent_rule_based
    intent, confidence = classify_intent_rule_based(text, current_step)
    return {'label': intent, 'confidence': confidence}