import re

class LLMGuardrails:
    def __init__(self):
        self.max_length = 400  # Increased for more natural responses
        self.prohibited_patterns = [
            r'\b\d{6,}\b',  # No long numbers (potential PII)
            r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',  # No emails
            r'\b\d{3}[-.]?\s?\d{3}[-.]?\s?\d{4}\b',  # No phone numbers
            r'\bABN\s*\d+\b',  # Australian Business Numbers
            r'\bTFN\s*\d+\b',  # Tax File Numbers
        ]
        
        # Medical/clinical terms to avoid
        self.medical_terms = [
            r'\bdiagnos[ei]s?\b', r'\bprescrib[ei]?\b', r'\bmedication\b',
            r'\bantidepressant\b', r'\btherapy session\b', r'\bclinical\b',
            r'\btreatment plan\b', r'\bmental illness\b', r'\bdisorder\b',
            r'\bcounseling\b', r'\bpsychologist\b', r'\bpsychiatrist\b'
        ]
        
        # Inappropriate cultural terms to avoid
        self.inappropriate_cultural = [
            r'\baboriginal problem\b', r'\btypical aboriginal\b',
            r'\baboriginal issue\b', r'\bprimitive\b', r'\btribal mentality\b'
        ]

    def pre_process(self, prompt):
        # No additional text needed - system prompts already contain safety guidelines
        return prompt

    def post_process(self, response):
        if self.contains_prohibited_content(response):
            return None  # Trigger fallback
        if self.contains_medical_advice(response):
            return None  # Trigger fallback
        if self.contains_inappropriate_cultural_content(response):
            return None  # Trigger fallback
        return self.sanitize(response)

    def contains_prohibited_content(self, text):
        """Check for PII and sensitive information"""
        for pattern in self.prohibited_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def contains_medical_advice(self, text):
        """Check for medical/clinical advice that should be avoided"""
        for pattern in self.medical_terms:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for direct medical advice phrases
        medical_advice_phrases = [
            "you should take", "i recommend medication", "you need therapy",
            "you have depression", "you are diagnosed", "take these pills"
        ]
        
        text_lower = text.lower()
        for phrase in medical_advice_phrases:
            if phrase in text_lower:
                return True
        
        return False
    
    def contains_inappropriate_cultural_content(self, text):
        """Check for culturally inappropriate content"""
        for pattern in self.inappropriate_cultural:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def sanitize(self, text):
        """Clean up response text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove any remaining system artifacts
        text = re.sub(r'\b(Assistant|System|User):\s*', '', text)
        
        # Ensure response isn't too long
        if len(text) > self.max_length:
            # Try to cut at sentence boundary
            sentences = text.split('. ')
            truncated = ''
            for sentence in sentences:
                if len(truncated + sentence + '. ') <= self.max_length:
                    truncated += sentence + '. '
                else:
                    break
            if truncated:
                text = truncated.rstrip('. ') + '.'
            else:
                text = text[:self.max_length].rstrip() + '...'
        
        return text
