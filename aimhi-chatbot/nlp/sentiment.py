# chatbot/aimhi-chatbot/nlp/sentiment.py

import logging
import os
from typing import Tuple, Dict

# Use a try-except block for optional dependencies.
try:
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Import the fallback function which has no heavy dependencies.
from fallbacks.keyword_sentiment import analyze_sentiment_keywords

logger = logging.getLogger(__name__)

class TwitterRoBERTaSentiment:
    """
    Singleton class for the Twitter-RoBERTa sentiment analyzer.
    Ensures the large model is loaded into memory only once.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TwitterRoBERTaSentiment, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.model = None
        self.tokenizer = None
        self.labels = []
        self.device = None

        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers library not found. Sentiment analysis will rely on keyword fallback.")
            self._initialized = True
            return

        try:
            model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
            logger.info(f"Attempting to load Twitter-RoBERTa model: {model_name}")

            config = AutoConfig.from_pretrained(model_name)

            # --- Robust Label Loading (from code-samir) ---
            if getattr(config, "id2label", None):
                self.labels = [config.id2label[i] for i in sorted(config.id2label.keys())]
                logger.info(f"Loaded labels from model config: {self.labels}")
            else:
                self.labels = ["negative", "neutral", "positive"]
                logger.warning(f"id2label not found in model config. Using default labels: {self.labels}")

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()

            logger.info(f"Twitter-RoBERTa model loaded successfully on device: {self.device}")

        except Exception as e:
            logger.error(f"Failed to load Twitter-RoBERTa model: {e}. Will use keyword fallback.", exc_info=True)
            self.model = None # Ensure fallback is used
        
        self._initialized = True

    def analyze(self, text: str) -> Tuple[str, float, str]:
        """
        Analyzes the sentiment of a given text.
        Returns a tuple of (label, confidence, method).
        """
        if not self.model or not self.tokenizer:
            label, confidence = analyze_sentiment_keywords(text)
            return label, confidence, 'keyword_fallback'
        
        if not text or not text.strip():
            return 'neutral', 0.5, 'no_input'

        try:
            inputs = self.tokenizer(
                text, return_tensors="pt", truncation=True, padding=True, max_length=512
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
            
            prediction_idx = int(probs.argmax())
            # Normalize the label to lowercase to be consistent (e.g., 'Positive' -> 'positive')
            predicted_label = self.labels[prediction_idx].lower()
            confidence = float(probs[prediction_idx])
            
            return predicted_label, confidence, 'twitter_roberta'

        except Exception as e:
            logger.error(f"Error during RoBERTa analysis: {e}. Falling back to keywords.", exc_info=True)
            label, confidence = analyze_sentiment_keywords(text)
            return label, confidence, 'keyword_fallback_on_error'


# --- Public API Function ---
def analyze_sentiment(text: str) -> Dict[str, any]:
    """
    Analyzes user sentiment using the singleton Twitter-RoBERTa instance.
    """
    analyzer_instance = TwitterRoBERTaSentiment()
    label, confidence, method = analyzer_instance.analyze(text)

    return {
        'label': label,
        'confidence': confidence,
        'method': method
    }