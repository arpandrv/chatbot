import re

class LLMGuardrails:
    def __init__(self):
        self.max_length = 150
        self.prohibited_patterns = [
            r'\b\d{6,}\b',  # No long numbers (potential PII)
            r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',  # No emails
            r'\b\d{3}[-.]?\s?\d{3}[-.]?\s?\d{4}\b',  # No phone numbers
        ]
        self.required_tone_check = True

    def pre_process(self, prompt):
        return prompt + "\nRemember: Be supportive, brief, and never give medical advice."

    def post_process(self, response):
        if self.contains_prohibited_content(response):
            return None  # Trigger fallback
        return self.sanitize(response)

    def contains_prohibited_content(self, text):
        for pattern in self.prohibited_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def sanitize(self, text):
        # Add any other sanitization logic here
        return text.strip()
