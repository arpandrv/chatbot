"""
Sentiment Analysis Module
=========================
Analyzes user sentiment to help select appropriate response tone.
Uses Twitter-RoBERTa model trained on 124M tweets for accurate sentiment detection
of informal language, slang, and youth expressions.
"""

import logging
from typing import Tuple, Dict, Optional
import warnings
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

# Try to import transformer libraries
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    import torch.nn.functional as F
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("Transformers not available. Install with: pip install transformers torch")
    TRANSFORMERS_AVAILABLE = False

class TwitterRoBERTaSentiment:
    """
    Twitter-RoBERTa sentiment analyzer optimized for social media and informal text.
    Singleton pattern for efficient model loading.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.model = None
        self.tokenizer = None
        self.device = None
        self.labels = ['negative', 'neutral', 'positive']
        
        if TRANSFORMERS_AVAILABLE:
            try:
                self.model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
                logger.info(f"Loading Twitter-RoBERTa model: {self.model_name}")
                
                # Set device
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                
                # Load tokenizer and model
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
                self.model.to(self.device)
                self.model.eval()
                
                logger.info(f"Twitter-RoBERTa loaded successfully on {self.device}")
                self._initialized = True
                
            except Exception as e:
                logger.error(f"Failed to load Twitter-RoBERTa: {e}")
                self.model = None
                self.tokenizer = None
        else:
            logger.warning("Transformers not available, using fallback")
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for Twitter-RoBERTa.
        Handles @mentions, URLs, and special characters.
        """
        if not text or not text.strip():
            return ""
        
        import re
        # Replace usernames with @user token
        text = re.sub(r'@\w+', '@user', text)
        # Replace URLs with http token  
        text = re.sub(r'http\S+|www.\S+', 'http', text)
        
        return text.strip()
    
    def analyze(self, text: str) -> Tuple[str, float]:
        """
        Analyze sentiment using Twitter-RoBERTa.
        Falls back to keyword matching if model unavailable.
        """
        if not self.model or not self.tokenizer:
            # Fallback to keyword matching
            return fallback_keyword_sentiment(text)
        
        # Preprocess
        processed_text = self.preprocess_text(text)
        
        if not processed_text:
            return 'neutral', 0.5
        
        try:
            # Tokenize
            inputs = self.tokenizer(
                processed_text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            ).to(self.device)
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = F.softmax(logits, dim=-1).cpu().numpy()[0]
            
            # Get predicted label and confidence
            predicted_idx = probs.argmax()
            predicted_label = self.labels[predicted_idx]
            confidence = float(probs[predicted_idx])
            
            return predicted_label, confidence
            
        except Exception as e:
            logger.error(f"Error in Twitter-RoBERTa analysis: {e}")
            return fallback_keyword_sentiment(text)


def fallback_keyword_sentiment(text: str) -> Tuple[str, float]:
    """
    Fallback keyword-based sentiment analysis.
    Used when Twitter-RoBERTa is unavailable.
    """
    if not text:
        return 'neutral', 0.5
    
    text_lower = text.lower()
    
    positive_keywords = ['good', 'great', 'happy', 'love', 'excited', 'awesome', 
                        'wonderful', 'amazing', 'fantastic', 'excellent', 'deadly',
                        'stoked', 'lit', 'sweet']
    negative_keywords = ['bad', 'sad', 'worried', 'stressed', 'angry', 'hate',
                        'terrible', 'awful', 'horrible', 'upset', 'shame', 'crook',
                        'cooked', 'mid']
    
    # Count keyword matches
    positive_count = sum(1 for word in positive_keywords if word in text_lower)
    negative_count = sum(1 for word in negative_keywords if word in text_lower)
    
    # Determine sentiment
    if positive_count > negative_count:
        confidence = min(positive_count * 0.3, 1.0)
        return 'positive', confidence
    elif negative_count > positive_count:
        confidence = min(negative_count * 0.3, 1.0)
        return 'negative', confidence
    else:
        return 'neutral', 0.5


# Global instance
_roberta_analyzer = None

def analyze_sentiment(text: str) -> Tuple[str, float]:
    """
    Main sentiment analysis function using Twitter-RoBERTa.
    
    Args:
        text: User input message
        
    Returns:
        tuple: (sentiment_label, confidence)
            sentiment_label: 'positive', 'negative', or 'neutral'
            confidence: float between 0 and 1
    """
    global _roberta_analyzer
    if _roberta_analyzer is None:
        _roberta_analyzer = TwitterRoBERTaSentiment()
    
    return _roberta_analyzer.analyze(text)


def get_sentiment_label(text: str) -> str:
    """
    Simple wrapper that returns just the sentiment label.
    Maintains backward compatibility with existing code.
    
    Args:
        text: User input message
        
    Returns:
        str: 'positive', 'negative', or 'neutral'
    """
    sentiment, _ = analyze_sentiment(text)
    return sentiment


def get_sentiment_details(text: str) -> Dict:
    """
    Get detailed sentiment analysis including confidence scores.
    
    Args:
        text: User input message
        
    Returns:
        dict: Contains label, confidence, and method used
    """
    sentiment, confidence = analyze_sentiment(text)
    
    return {
        'label': sentiment,
        'confidence': confidence,
        'method': 'twitter-roberta' if TRANSFORMERS_AVAILABLE else 'keyword-fallback'
    }


# For testing purposes
if __name__ == "__main__":
    test_phrases = [
        "I love this!",
        "I hate everything",
        "It's okay I guess",
        "That's deadly, bro!",
        "I'm absolutely cooked",
        "This is so lit!",
        "I'm not happy at all",
        "Never been better"
    ]
    
    print("Testing Sentiment Analysis:")
    print("=" * 50)
    
    for phrase in test_phrases:
        result = get_sentiment_details(phrase)
        print(f"Text: '{phrase}'")
        print(f"  Sentiment: {result['label']} (confidence: {result['confidence']:.3f})")
        print(f"  Method: {result['method']}")
        print()