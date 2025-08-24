"""
Keyword-based Sentiment Analysis Fallback
==========================================
Traditional rule-based sentiment analysis using keyword matching.
Used when Twitter-RoBERTa model is unavailable.
"""

from typing import Tuple

def analyze_sentiment_keywords(text: str) -> Tuple[str, float]:
    """
    Fallback keyword-based sentiment analysis with word boundaries and negation.
    Used when Twitter-RoBERTa is unavailable.
    """
    import re
    
    if not text:
        return 'neutral', 0.5
    
    text_lower = text.lower()
    
    positive_keywords = ['good', 'great', 'happy', 'love', 'excited', 'awesome', 
                        'wonderful', 'amazing', 'fantastic', 'excellent', 'deadly',
                        'stoked', 'lit', 'sweet']
    negative_keywords = ['bad', 'sad', 'worried', 'stressed', 'angry', 'hate',
                        'terrible', 'awful', 'horrible', 'upset', 'shame', 'crook',
                        'cooked', 'mid']
    
    # Check for negation first
    negation_words = ['not', 'no', "n't", 'never']
    words = text_lower.split()
    
    positive_count = 0
    negative_count = 0
    
    # Count matches with word boundaries and negation handling
    for word in positive_keywords:
        matches = len(re.findall(rf'\b{word}\b', text_lower))
        # Check if negated
        negated_matches = len(re.findall(rf'\b(?:not|no|n\'t|never)\s+\w*\s*{word}\b', text_lower))
        positive_count += matches - negated_matches
        negative_count += negated_matches  # Negated positive becomes negative
    
    for word in negative_keywords:
        matches = len(re.findall(rf'\b{word}\b', text_lower))
        # Check if negated  
        negated_matches = len(re.findall(rf'\b(?:not|no|n\'t|never)\s+\w*\s*{word}\b', text_lower))
        negative_count += matches - negated_matches
        positive_count += negated_matches  # Negated negative becomes positive
    
    # Determine sentiment
    if positive_count > negative_count:
        confidence = min(positive_count * 0.3, 1.0)
        return 'positive', confidence
    elif negative_count > positive_count:
        confidence = min(negative_count * 0.3, 1.0)
        return 'negative', confidence
    else:
        return 'neutral', 0.5