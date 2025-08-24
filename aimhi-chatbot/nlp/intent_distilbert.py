#!/usr/bin/env python3
"""
RoBERTa Zero-Shot Intent Classification Module
AIMhi-Y Supportive Yarn Chatbot

This module provides a RoBERTa-based zero-shot intent classifier using the
FacebookAI/roberta-large-mnli model for natural language inference.

Features:
- Zero-shot classification without training
- Context-aware confidence boosting based on FSM state
- Text preprocessing pipeline
- Confidence thresholding with fallback to 'unclear'
- Optimized for inference speed using ONNX Runtime
- Cultural context awareness for Aboriginal and Torres Strait Islander youth
"""

import os
import json
import logging
import re
import time
from typing import Tuple, Optional, Dict, Any, List
import warnings
warnings.filterwarnings('ignore')

import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

# Try to import required libraries
try:
    from transformers import AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not available, will use fallback")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("onnxruntime not available, install with: pip install onnxruntime")

class RoBERTaZeroShotClassifier:
    """
    RoBERTa Zero-Shot Intent Classifier with Singleton Pattern
    
    Uses the roberta-large-mnli model for zero-shot classification
    of user intents through natural language inference via ONNX Runtime.
    """
    
    _instance = None
    _session = None
    _tokenizer = None
    _is_initialized = False
    
    # Intent labels and their corresponding hypothesis templates
    INTENT_TEMPLATES = {
        'greeting': [
            "This is a greeting or hello",
            "The user is saying hello",
            "This is a friendly greeting"
        ],
        'question': [
            "This is a question",
            "The user is asking something",
            "The user wants information"
        ],
        'affirmative': [
            "The user agrees or says yes",
            "This is a positive response",
            "The user is affirming"
        ],
        'negative': [
            "The user disagrees or says no",
            "This is a negative response",
            "The user is declining"
        ],
        'support_people': [
            "The user is talking about people who support them",
            "This mentions family or friends who help",
            "The user describes their support network"
        ],
        'strengths': [
            "The user is talking about their strengths or abilities",
            "This mentions things they are good at",
            "The user describes their skills or talents"
        ],
        'worries': [
            "The user is talking about worries or concerns",
            "This mentions stress or anxiety",
            "The user describes what bothers them"
        ],
        'goals': [
            "The user is talking about goals or aspirations",
            "This mentions future plans or dreams",
            "The user describes what they want to achieve"
        ],
        'no_support': [
            "The user says they have no support",
            "The user mentions having nobody to help them",
            "This indicates lack of support network"
        ],
        'no_strengths': [
            "The user says they have no strengths",
            "The user mentions not being good at anything",
            "This indicates lack of abilities or skills"
        ],
        'no_worries': [
            "The user says they have no worries",
            "The user mentions not being concerned about anything",
            "This indicates absence of stress or anxiety"
        ],
        'no_goals': [
            "The user says they have no goals",
            "The user mentions not having plans or dreams",
            "This indicates absence of aspirations"
        ],
        'unclear': [
            "This message is unclear or confusing",
            "The meaning is ambiguous",
            "This doesn't fit any specific category"
        ]
    }
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(RoBERTaZeroShotClassifier, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the classifier (only once due to singleton pattern)."""
        if not self._is_initialized:
            self._load_model()
            self._is_initialized = True
    
    def _load_model(self):
        """Load the RoBERTa MNLI model (ONNX) and tokenizer."""
        try:
            # Determine model path
            current_dir = os.path.dirname(__file__)
            model_dir = os.path.join(current_dir, '..', 'ai_models', 'FacebookAI_roberta-large-mnli')
            
            if not os.path.exists(model_dir):
                # Try alternative path without FacebookAI prefix
                model_dir = os.path.join(current_dir, '..', 'ai_models', 'roberta-large-mnli')
            
            if not os.path.exists(model_dir):
                logger.warning(f"RoBERTa model not found at {model_dir}")
                self._session = None
                self._tokenizer = None
                return
            
            # Check for ONNX model
            onnx_path = os.path.join(model_dir, 'onnx', 'model_int8.onnx')
            if not os.path.exists(onnx_path):
                logger.warning(f"ONNX model not found at {onnx_path}")
                self._session = None
                self._tokenizer = None
                return
            
            # Check if ONNX Runtime is available
            if not ONNX_AVAILABLE:
                logger.error("ONNX Runtime not installed. Install with: pip install onnxruntime")
                self._session = None
                self._tokenizer = None
                return
            
            # Load ONNX model
            logger.info(f"Loading ONNX model from {onnx_path}")
            
            # Create ONNX Runtime session with optimization
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session_options.inter_op_num_threads = 2
            session_options.intra_op_num_threads = 4
            
            # Use CPU execution provider
            providers = ['CPUExecutionProvider']
            
            self._session = ort.InferenceSession(onnx_path, session_options, providers=providers)
            logger.info("ONNX model loaded successfully")
            
            # Load tokenizer
            if TRANSFORMERS_AVAILABLE:
                self._tokenizer = AutoTokenizer.from_pretrained(model_dir, use_fast=True)
                logger.info("Tokenizer loaded successfully")
            else:
                logger.error("Transformers library not available for tokenizer")
                self._session = None
                self._tokenizer = None
                return
            
            # Warmup
            try:
                dummy_text = "Hello"
                dummy_hypothesis = "This is a greeting"
                self._compute_entailment_score_onnx(dummy_text, dummy_hypothesis)
                logger.info("Model warmed up for inference")
            except Exception as e:
                logger.warning(f"Could not warm up model: {e}")
            
            logger.info("RoBERTa zero-shot model (ONNX) loaded successfully")
            logger.info(f"Model supports {len(self.INTENT_TEMPLATES)} intent classes")
            
        except Exception as e:
            logger.error(f"Failed to load RoBERTa model: {str(e)}")
            self._session = None
            self._tokenizer = None
    
    def is_available(self) -> bool:
        """Check if the model is available for inference."""
        return self._session is not None and self._tokenizer is not None
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for intent classification.
        
        Args:
            text: Raw user input text
            
        Returns:
            Preprocessed text ready for classification
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Handle common contractions
        contractions = {
            "i'm": "i am",
            "im": "i am", 
            "don't": "do not",
            "dont": "do not",
            "can't": "cannot",
            "cant": "cannot",
            "won't": "will not",
            "wont": "will not",
            "doesn't": "does not",
            "doesnt": "does not",
            "didn't": "did not",
            "didnt": "did not"
        }
        
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        # Handle cultural terms
        cultural_normalizations = {
            "mob": "family",
            "deadly": "good",
            "blackfella": "person",
            "whitefella": "person",
            "yarning": "talking",
            "yarn": "talk"
        }
        
        for cultural_term, normalized in cultural_normalizations.items():
            text = re.sub(rf'\b{cultural_term}\b', normalized, text)
        
        # Remove special characters while preserving important punctuation
        text = re.sub(r'[^\w\s\'-?!]', '', text)
        
        return text.strip()
    
    def _compute_entailment_score_onnx(self, text: str, hypothesis: str) -> float:
        """
        Compute entailment score using ONNX Runtime.
        
        Args:
            text: Input text to classify
            hypothesis: Hypothesis statement
            
        Returns:
            Entailment score
        """
        # Tokenize
        inputs = self._tokenizer(
            text,
            hypothesis,
            truncation=True,
            padding='max_length',
            max_length=256,
            return_tensors='np'  # Return NumPy arrays for ONNX
        )
        
        # Prepare input for ONNX
        ort_inputs = {
            'input_ids': inputs['input_ids'].astype(np.int64),
            'attention_mask': inputs['attention_mask'].astype(np.int64)
        }
        
        # Run inference
        ort_outputs = self._session.run(None, ort_inputs)
        
        # Get logits (first output)
        logits = ort_outputs[0][0]  # Shape: [3] for MNLI
        
        # Apply softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        
        # MNLI labels: 0=contradiction, 1=neutral, 2=entailment
        # Return entailment score
        return float(probs[2])
    
    def _compute_entailment_scores(self, text: str, hypotheses: List[str]) -> np.ndarray:
        """
        Compute entailment scores for text against multiple hypotheses.
        
        Args:
            text: Input text to classify
            hypotheses: List of hypothesis statements
            
        Returns:
            Array of entailment scores
        """
        scores = []
        
        for hypothesis in hypotheses:
            score = self._compute_entailment_score_onnx(text, hypothesis)
            scores.append(score)
        
        return np.array(scores)
    
    def _apply_context_boosting(self, scores: Dict[str, float], current_step: Optional[str]) -> Dict[str, float]:
        """
        Apply context-aware boosting based on FSM state.
        
        Args:
            scores: Dictionary of intent scores
            current_step: Current FSM state for context
            
        Returns:
            Adjusted scores with context boosting
        """
        if not current_step:
            return scores
        
        boosted_scores = scores.copy()
        
        # Context-based boosting factors
        context_boosts = {
            'support_people': {
                'support_people': 1.4,
                'no_support': 1.3,
                'strengths': 0.7,
                'worries': 0.8
            },
            'strengths': {
                'strengths': 1.4,
                'no_strengths': 1.3,
                'support_people': 0.7,
                'worries': 0.8
            },
            'worries': {
                'worries': 1.4,
                'no_worries': 1.3,
                'negative': 1.1,
                'strengths': 0.8
            },
            'goals': {
                'goals': 1.4,
                'no_goals': 1.3,
                'affirmative': 1.1,
                'worries': 0.8
            },
            'welcome': {
                'greeting': 1.3,
                'question': 1.2,
                'affirmative': 1.1
            },
            'summary': {
                'affirmative': 1.3,
                'negative': 1.2,
                'question': 1.1
            }
        }
        
        if current_step in context_boosts:
            step_boosts = context_boosts[current_step]
            
            for intent_name, boost_factor in step_boosts.items():
                if intent_name in boosted_scores:
                    boosted_scores[intent_name] *= boost_factor
        
        return boosted_scores
    
    def classify_intent(self, text: str, current_step: Optional[str] = None, 
                       confidence_threshold: float = 0.25) -> Tuple[str, float]:
        """
        Classify intent using zero-shot classification.
        
        Args:
            text: User input text
            current_step: Current FSM state for context boosting
            confidence_threshold: Minimum confidence for prediction
            
        Returns:
            Tuple of (intent_label, confidence_score)
        """
        start_time = time.time()
        
        # Check if model is available
        if not self.is_available():
            logger.warning("RoBERTa model not available, returning unclear")
            return 'unclear', 0.0
        
        # Handle empty input
        if not text or not text.strip():
            return 'unclear', 0.0
        
        try:
            # Preprocess text
            processed_text = self._preprocess_text(text)
            
            if not processed_text:
                return 'unclear', 0.0
            
            # Compute scores for each intent
            intent_scores = {}
            
            for intent, hypotheses in self.INTENT_TEMPLATES.items():
                if intent == 'unclear':
                    continue  # Skip unclear, it's the default
                
                # Get entailment scores for all hypotheses of this intent
                scores = self._compute_entailment_scores(processed_text, hypotheses)
                
                # Use max score across hypotheses for this intent
                intent_scores[intent] = float(np.max(scores))
            
            # Apply context boosting
            intent_scores = self._apply_context_boosting(intent_scores, current_step)
            
            # Get best intent
            if intent_scores:
                best_intent = max(intent_scores.items(), key=lambda x: x[1])
                intent_label, confidence = best_intent
                
                # Apply confidence threshold
                if confidence < confidence_threshold:
                    intent_label = 'unclear'
                
                # Check if multiple intents have similar high scores (ambiguous)
                sorted_scores = sorted(intent_scores.values(), reverse=True)
                if len(sorted_scores) > 1:
                    margin = sorted_scores[0] - sorted_scores[1]
                    if margin < 0.1:  # Too close to call
                        intent_label = 'unclear'
            else:
                intent_label = 'unclear'
                confidence = 0.0
            
            # Log inference time
            inference_time = (time.time() - start_time) * 1000
            if inference_time > 100:
                logger.warning(f"Slow inference: {inference_time:.1f}ms for text: '{text[:50]}...'")
            
            return intent_label, confidence
            
        except Exception as e:
            logger.error(f"Error during zero-shot classification: {str(e)}")
            return 'unclear', 0.0
    
    def classify_question_subtype(self, text: str) -> str:
        """
        Sub-classify question intents into identity or help questions.
        
        Args:
            text: User input text classified as 'question'
            
        Returns:
            Question subtype: 'identity_question', 'help_question', or 'general_question'
        """
        if not text:
            return 'general_question'
        
        text_lower = text.lower()
        
        # Identity question markers
        identity_markers = [
            "who are you", "what are you", "your name", "are you yarn",
            "are you a bot", "are you a chatbot", "are you real",
            "what's your name", "whats your name", "who am i talking to"
        ]
        
        # Help question markers  
        help_markers = [
            "can you help", "need help", "support me", "what can you do",
            "how can you help", "what do you do", "help me", "assist me"
        ]
        
        # Check for identity questions
        for marker in identity_markers:
            if marker in text_lower:
                return 'identity_question'
        
        # Check for help questions
        for marker in help_markers:
            if marker in text_lower:
                return 'help_question'
        
        return 'general_question'
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        if not self.is_available():
            return {'available': False, 'error': 'Model not loaded'}
        
        return {
            'available': True,
            'model_type': 'RoBERTa-large-MNLI (ONNX zero-shot)',
            'num_classes': len(self.INTENT_TEMPLATES),
            'intent_classes': list(self.INTENT_TEMPLATES.keys()),
            'runtime': 'ONNX Runtime',
            'optimization': 'INT8 quantized'
        }

# Global instance for easy import
roberta_classifier = RoBERTaZeroShotClassifier()

def classify_intent_distilbert(text: str, current_step: Optional[str] = None, 
                              confidence_threshold: float = 0.25) -> Tuple[str, float]:
    """
    Convenience function for intent classification using RoBERTa zero-shot.
    Named to maintain backward compatibility with existing code.
    
    Args:
        text: User input text
        current_step: Current FSM state for context boosting
        confidence_threshold: Minimum confidence for prediction
        
    Returns:
        Tuple of (intent_label, confidence_score)
    """
    try:
        return roberta_classifier.classify_intent(text, current_step, confidence_threshold)
    except Exception as e:
        logger.error(f"RoBERTa classification failed: {e}")
        return 'unclear', 0.0

def is_distilbert_available() -> bool:
    """Check if RoBERTa model is available for use."""
    return roberta_classifier.is_available()

def get_distilbert_info() -> Dict[str, Any]:
    """Get information about the RoBERTa model."""
    return roberta_classifier.get_model_info()

def classify_intent(text: str, current_step: Optional[str] = None) -> Dict[str, Any]:
    """
    Unified intent classification with automatic fallback.
    
    Uses RoBERTa zero-shot as primary method with rule-based fallback for low confidence
    or when RoBERTa is unavailable.
    
    Args:
        text: User input text
        current_step: Current FSM state for context
        
    Returns:
        Dict containing: label, confidence, method
    """
    if not text or not text.strip():
        return {
            'label': 'unclear',
            'confidence': 0.0,
            'method': 'empty_input'
        }
    
    intent, confidence = None, 0.0
    method = 'unknown'
    
    # Try RoBERTa zero-shot first if available
    if is_distilbert_available():
        try:
            intent, confidence = classify_intent_distilbert(text, current_step, confidence_threshold=0.3)
            method = 'roberta_zero_shot_onnx'
            logger.debug(f"RoBERTa zero-shot classification: {intent} ({confidence:.3f})")
            
            # If RoBERTa gives low confidence, try rule-based fallback
            if confidence < 0.3:
                try:
                    from fallbacks.rule_based_intent import classify_intent_rule_based
                    rule_intent, rule_confidence = classify_intent_rule_based(text, current_step=current_step)
                    logger.debug(f"Rule-based fallback: {rule_intent} ({rule_confidence:.3f})")
                    
                    # Use rule-based if it has higher confidence
                    if rule_confidence > confidence * 1.2:
                        intent, confidence = rule_intent, rule_confidence
                        method = 'rule_based_fallback'
                        logger.debug(f"Switched to rule-based: {intent} ({confidence:.3f})")
                except ImportError:
                    # If fallback module doesn't exist, try the main intent module
                    from nlp.intent import classify_intent as classify_intent_rule
                    rule_result = classify_intent_rule(text, current_step=current_step)
                    if isinstance(rule_result, dict):
                        rule_intent = rule_result.get('label', 'unclear')
                        rule_confidence = rule_result.get('confidence', 0.0)
                    else:
                        rule_intent, rule_confidence = rule_result
                    
                    if rule_confidence > confidence * 1.2:
                        intent, confidence = rule_intent, rule_confidence
                        method = 'rule_based_fallback'
                    
        except Exception as e:
            logger.warning(f"RoBERTa classification failed, using rule-based: {e}")
            try:
                from fallbacks.rule_based_intent import classify_intent_rule_based
                intent, confidence = classify_intent_rule_based(text, current_step=current_step)
                method = 'rule_based_error_fallback'
            except ImportError:
                from nlp.intent import classify_intent as classify_intent_rule
                rule_result = classify_intent_rule(text, current_step=current_step)
                if isinstance(rule_result, dict):
                    intent = rule_result.get('label', 'unclear')
                    confidence = rule_result.get('confidence', 0.0)
                else:
                    intent, confidence = rule_result
                method = 'rule_based_error_fallback'
    else:
        # Fall back to rule-based system when RoBERTa unavailable
        logger.info("RoBERTa model not available, using rule-based classification")
        try:
            from fallbacks.rule_based_intent import classify_intent_rule_based
            intent, confidence = classify_intent_rule_based(text, current_step=current_step)
            method = 'rule_based_primary'
        except ImportError:
            from nlp.intent import classify_intent as classify_intent_rule
            rule_result = classify_intent_rule(text, current_step=current_step)
            if isinstance(rule_result, dict):
                intent = rule_result.get('label', 'unclear')
                confidence = rule_result.get('confidence', 0.0)
            else:
                intent, confidence = rule_result
            method = 'rule_based_primary'
    
    # Normalize intent names between systems
    intent_mapping = {
        'affirmative': 'affirmation',
        'negative': 'negation'
    }
    intent = intent_mapping.get(intent, intent)
    
    return {
        'label': intent,
        'confidence': confidence,
        'method': method
    }

# Example usage and testing
if __name__ == "__main__":
    # Test the classifier
    classifier = RoBERTaZeroShotClassifier()
    
    if classifier.is_available():
        test_cases = [
            ("hello there", "welcome"),
            ("my family supports me", "support_people"),
            ("i'm good at football", "strengths"),
            ("i worry about school", "worries"),
            ("i want to get a job", "goals"),
            ("who are you", None),
            ("can you help me", None),
            ("not really", None),
            ("yeah", None),
            ("no", None),
            ("", None)
        ]
        
        print("=== RoBERTa Zero-Shot Intent Classification Test (ONNX) ===")
        for text, step in test_cases:
            intent, confidence = classifier.classify_intent(text, step)
            print(f"Text: '{text}' | Step: {step} | Intent: {intent} | Confidence: {confidence:.3f}")
            
            if intent == 'question':
                subtype = classifier.classify_question_subtype(text)
                print(f"  Question subtype: {subtype}")
        
        print(f"\nModel Info: {classifier.get_model_info()}")
    else:
        print("RoBERTa model not available. Please ensure:")
        print("1. ONNX model exists at ai_models/FacebookAI_roberta-large-mnli/onnx/model_int8.onnx")
        print("2. Install required packages: pip install onnxruntime transformers")