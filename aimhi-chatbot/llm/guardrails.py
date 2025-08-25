# aimhi-chatbot/llm/guardrails.py

"""
Hybrid LLM Guardrails - Configuration-driven with comprehensive filtering.
Combines the maintainability of config-driven patterns with comprehensive coverage.
"""

import re
import json
import os
import logging
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# Compile patterns at module level - once per process
_PII_PATTERNS = [
    re.compile(r'\b(?:\+61\s?|0)[2-9]\d{8}\b', re.IGNORECASE),  # Australian phone
    re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', re.IGNORECASE),  # US phone
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE),  # Email
    re.compile(r'\bABN\s*:?\s*\d{11}\b', re.IGNORECASE),  # Australian Business Number
    re.compile(r'\bTFN\s*:?\s*\d{8,9}\b', re.IGNORECASE),  # Tax File Number
    re.compile(r'\bBSB\s*:?\s*\d{3}[-\s]?\d{3}\b', re.IGNORECASE),  # Bank BSB
    re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', re.IGNORECASE),  # Credit card
    re.compile(r'\b\d{8,}\b', re.IGNORECASE)  # Long numbers (potential IDs)
]

_MEDICAL_PATTERNS = [
    re.compile(r'\byou should take\s+(?:medication|pills|drugs)', re.IGNORECASE),
    re.compile(r'\bi (?:recommend|suggest|prescribe)\s+(?:medication|pills|drugs)', re.IGNORECASE),
    re.compile(r'\byou (?:have|are diagnosed with)\s+(?:depression|anxiety|adhd|bipolar)', re.IGNORECASE),
    re.compile(r'\btake these (?:pills|medications|drugs)', re.IGNORECASE),
    re.compile(r'\bi diagnose you with\b', re.IGNORECASE),
    re.compile(r'\byour (?:disorder|condition|illness) is\b', re.IGNORECASE)
]

_CULTURAL_PATTERNS = [
    re.compile(r'\b(?:typical|all|most)\s+aboriginal\s+(?:people|kids|youth|problems)', re.IGNORECASE),
    re.compile(r'\baboriginal\s+(?:problems|issues|mentality)\b', re.IGNORECASE),
    re.compile(r'\b(?:primitive|savage|backward|uncivilized)\b', re.IGNORECASE),
    re.compile(r'\btribal\s+mentality\b', re.IGNORECASE),
    re.compile(r'\b(?:real|proper|full-blood)\s+aboriginal\b', re.IGNORECASE)
]

_QUALITY_PATTERNS = [
    re.compile(r'^(?:I cannot|I can\'t|I\'m not able to|I don\'t have access)', re.IGNORECASE),
    re.compile(r'\b(?:API error|Error:|Failed to|unauthorized|rate limit)\b', re.IGNORECASE),
    re.compile(r'\b(?:null|undefined|NaN|\.\.\.+)\b', re.IGNORECASE),
    re.compile(r'^(?:umm|uh|er|well,?\s*$)', re.IGNORECASE)
]


class LLMGuardrails:
    """
    A robust, configuration-driven guardrail system for LLM interactions.
    Uses pre-compiled patterns for optimal performance.
    """
    
    def __init__(self):
        """Initialize guardrails by loading settings from config."""
        self._load_config()
        # Use the pre-compiled patterns
        self.pii_patterns = _PII_PATTERNS
        self.medical_patterns = _MEDICAL_PATTERNS
        self.cultural_patterns = _CULTURAL_PATTERNS
        self.quality_patterns = _QUALITY_PATTERNS
        self._compile_additional_patterns()
        logger.info("LLMGuardrails initialized with pre-compiled patterns.")

    def _load_config(self):
        """Load guardrail settings from llm_config.json with smart defaults."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, '..', 'config', 'llm_config.json')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Load settings from the 'guardrails' section
            guardrail_config = config.get('guardrails', {})
            
            # Basic settings
            self.max_length = guardrail_config.get('max_response_length', 400)
            self.safety_preamble = guardrail_config.get('safety_preamble', self._default_safety_preamble())
            
            # Feature flags
            self.enable_pii_filter = guardrail_config.get('enable_pii_filter', True)
            self.enable_medical_filter = guardrail_config.get('enable_medical_filter', True)
            self.enable_cultural_filter = guardrail_config.get('enable_cultural_filter', True)
            self.enable_quality_filter = guardrail_config.get('enable_quality_filter', True)
            self.truncate_at_sentence = guardrail_config.get('truncate_at_sentence', True)
            self.allow_supportive_mentions = guardrail_config.get('allow_supportive_mentions', True)
            
            # Configurable patterns (can be customized in JSON)
            self.custom_pii_patterns = guardrail_config.get('prohibited_pii_patterns', [])
            self.custom_medical_terms = guardrail_config.get('prohibited_medical_terms', [])
            self.custom_cultural_terms = guardrail_config.get('prohibited_cultural_terms', [])
            
            logger.info("Guardrail configuration loaded successfully")
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load guardrail config: {e}. Using defaults.")
            self._use_default_config()

    def _use_default_config(self):
        """Fallback to default configuration."""
        self.max_length = 400
        self.safety_preamble = self._default_safety_preamble()
        self.enable_pii_filter = True
        self.enable_medical_filter = True
        self.enable_cultural_filter = True
        self.enable_quality_filter = True
        self.truncate_at_sentence = True
        self.allow_supportive_mentions = True
        self.custom_pii_patterns = []
        self.custom_medical_terms = []
        self.custom_cultural_terms = []

    def _default_safety_preamble(self) -> str:
        """Default safety instructions to inject into prompts."""
        return ("Remember: Be supportive and culturally respectful. Never provide medical "
                "diagnoses, prescribe medications, or give clinical advice. Focus on listening "
                "and encouraging professional help when appropriate.")

    def _compile_additional_patterns(self):
        """Compile any custom patterns from config."""
        # Supportive medical context indicators (non-regex)
        self.supportive_medical_indicators = [
            'might help to', 'could consider', 'talking to', 'reaching out to',
            'if you feel comfortable', 'when you\'re ready', 'support is available'
        ]
        
        # Add any custom patterns from config if needed
        custom_pii = getattr(self, 'custom_pii_patterns', [])
        if custom_pii:
            self.pii_patterns.extend([re.compile(pattern, re.IGNORECASE) for pattern in custom_pii])
        
        custom_cultural = getattr(self, 'custom_cultural_terms', [])
        if custom_cultural:
            self.cultural_patterns.extend([re.compile(term, re.IGNORECASE) for term in custom_cultural])

    def pre_process(self, prompt: str) -> str:
        """
        Apply pre-processing guardrails (safety preamble injection).
        """
        if not isinstance(prompt, str):
            return str(prompt)
            
        if self.safety_preamble and self.safety_preamble.lower() not in prompt.lower():
            return f"{self.safety_preamble}\n\n{prompt}"
        
        return prompt

    def post_process(self, response: str) -> Optional[str]:
        """
        Apply all post-processing guardrails and return sanitized response or None if blocked.
        """
        if not response or not isinstance(response, str):
            logger.warning("Guardrails received empty or invalid response")
            return None

        try:
            # Apply filters based on configuration
            if self.enable_pii_filter and self._contains_pii(response):
                logger.warning("Response blocked: Contains PII")
                return None
            
            if self.enable_medical_filter and self._contains_inappropriate_medical_advice(response):
                logger.warning("Response blocked: Contains inappropriate medical advice")
                return None
                
            if self.enable_cultural_filter and self._contains_inappropriate_cultural_content(response):
                logger.warning("Response blocked: Contains inappropriate cultural content")
                return None
            
            if self.enable_quality_filter and self._is_low_quality_response(response):
                logger.warning("Response blocked: Low quality response")
                return None
            
            # Sanitize and return
            return self.sanitize(response)
            
        except Exception as e:
            logger.error(f"Error in post-processing guardrails: {e}")
            return None

    def _contains_pii(self, text: str) -> bool:
        """Check for PII using compiled patterns."""
        for pattern in self.pii_patterns:
            if pattern.search(text):
                return True
        return False

    def _contains_inappropriate_medical_advice(self, text: str) -> bool:
        """Check for inappropriate medical advice with context awareness."""
        # Always block direct medical advice
        for pattern in self.medical_patterns:
            if pattern.search(text):
                return True
        
        # Check custom medical terms from config
        text_lower = text.lower()
        for term in self.custom_medical_terms:
            if term.lower() in text_lower:
                # If supportive mentions allowed, check context
                if self.allow_supportive_mentions:
                    has_supportive_context = any(
                        indicator in text_lower 
                        for indicator in self.supportive_medical_indicators
                    )
                    if not has_supportive_context:
                        return True
                else:
                    return True
        
        return False

    def _contains_inappropriate_cultural_content(self, text: str) -> bool:
        """Check for culturally inappropriate content."""
        # Check compiled patterns
        for pattern in self.cultural_patterns:
            if pattern.search(text):
                return True
        
        # Check simple custom terms
        text_lower = text.lower()
        for term in self.custom_cultural_terms:
            if isinstance(term, str) and term.lower() in text_lower:
                return True
        
        return False

    def _is_low_quality_response(self, text: str) -> bool:
        """Check for low quality responses."""
        # Basic length check
        if len(text.strip()) < 10:
            return True
        
        # Check quality patterns
        for pattern in self.quality_patterns:
            if pattern.search(text):
                return True
        
        # Word count check
        words = text.strip().split()
        if len(words) < 3:
            return True
        
        return False

    def sanitize(self, text: str) -> str:
        """
        Clean and truncate response text intelligently.
        Combines the best truncation logic from both approaches.
        """
        # Remove extra whitespace and system artifacts
        sanitized_text = re.sub(r'\s+', ' ', text).strip()
        sanitized_text = re.sub(r'\b(Assistant|System|User):\s*', '', sanitized_text, flags=re.IGNORECASE)
        
        # Remove markdown artifacts
        sanitized_text = re.sub(r'```\w*\n?', '', sanitized_text)
        sanitized_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', sanitized_text)
        sanitized_text = re.sub(r'\*([^*]+)\*', r'\1', sanitized_text)
        
        # Smart truncation if needed
        if len(sanitized_text) > self.max_length:
            if self.truncate_at_sentence:
                # Enhanced sentence-boundary truncation
                truncated_text = sanitized_text[:self.max_length]
                
                # Find the last sentence-ending punctuation
                last_punc_pos = max(
                    truncated_text.rfind('.'),
                    truncated_text.rfind('?'),
                    truncated_text.rfind('!')
                )
                
                # If punctuation found and leaves meaningful content
                if last_punc_pos > len(sanitized_text) * 0.5:  # At least 50% of original
                    sanitized_text = truncated_text[:last_punc_pos + 1]
                else:
                    # Fallback: word boundary truncation
                    words = sanitized_text.split()
                    truncated_words = []
                    current_length = 0
                    
                    for word in words:
                        if current_length + len(word) + 1 <= self.max_length - 3:
                            truncated_words.append(word)
                            current_length += len(word) + 1
                        else:
                            break
                    
                    if truncated_words:
                        sanitized_text = ' '.join(truncated_words) + '...'
                    else:
                        sanitized_text = sanitized_text[:self.max_length - 3] + '...'
            else:
                # Hard truncation with word boundary
                sanitized_text = sanitized_text[:self.max_length].rsplit(' ', 1)[0] + "..."
        
        return sanitized_text.strip()

    def get_config_info(self) -> Dict[str, Any]:
        """Get current configuration information."""
        return {
            'max_length': self.max_length,
            'filters_enabled': {
                'pii_filter': self.enable_pii_filter,
                'medical_filter': self.enable_medical_filter,
                'cultural_filter': self.enable_cultural_filter,
                'quality_filter': self.enable_quality_filter
            },
            'pattern_counts': {
                'pii_patterns': len(self.pii_patterns),
                'medical_patterns': len(self.medical_patterns),
                'cultural_patterns': len(self.cultural_patterns),
                'quality_patterns': len(self.quality_patterns)
            },
            'custom_pattern_counts': {
                'custom_pii': len(self.custom_pii_patterns),
                'custom_medical': len(self.custom_medical_terms),
                'custom_cultural': len(self.custom_cultural_terms)
            },
            'supportive_mentions_allowed': self.allow_supportive_mentions,
            'truncate_at_sentence': self.truncate_at_sentence
        }

    # Legacy compatibility methods
    def contains_pii(self, text: str) -> bool:
        """Legacy compatibility method."""
        return self._contains_pii(text)
    
    def contains_medical_advice(self, text: str) -> bool:
        """Legacy compatibility method.""" 
        return self._contains_inappropriate_medical_advice(text)
    
    def contains_inappropriate_cultural_content(self, text: str) -> bool:
        """Legacy compatibility method."""
        return self._contains_inappropriate_cultural_content(text)