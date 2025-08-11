import os
import aiohttp
import json

class LLMClient:
    def __init__(self, model_name="anthropic/claude-3-haiku", timeout=30.0):
        self.model = model_name
        self.timeout = timeout
        self.max_tokens = 500
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.site_url = os.getenv('SITE_URL', 'https://aimhi-chatbot.local')
        self.site_name = os.getenv('SITE_NAME', 'AIMhi-Y Supportive Yarn Chatbot')

    async def generate(self, prompt, temperature=0.7):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "frequency_penalty": 0.1
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=data, timeout=self.timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter API error {response.status}: {error_text}")
                
                result = await response.json()
                return result['choices'][0]['message']['content']

    def generate_sync(self, prompt, temperature=0.7):
        """Synchronous wrapper for the async generate method"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.generate(prompt, temperature))
    
    def validate_response(self, text):
        """Validate LLM response"""
        if not text or not isinstance(text, str):
            return False
        
        # Check for reasonable length
        if len(text.strip()) < 5 or len(text) > self.max_tokens * 4:
            return False
        
        # Check for error indicators
        error_indicators = [
            "I cannot", "I can't", "I'm not able to", "I don't have access",
            "API error", "Error:", "Failed to", "unauthorized"
        ]
        
        text_lower = text.lower()
        if any(error in text_lower for error in error_indicators):
            return False
        
        return True
