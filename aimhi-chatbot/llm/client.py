import os
import aiohttp
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available

class LLMClient:
    def __init__(self, config_type="conversation"):
        # Load config from JSON
        self._load_config()
        
        # Set parameters based on config type (conversation or summary)
        params = self.config['parameters'].get(config_type, self.config['parameters']['conversation'])
        
        self.model = self.config['models']['primary']
        self.timeout = params['timeout']
        self.max_tokens = params['max_tokens']
        self.temperature = params['temperature']
        
        # Environment variables (secrets)
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.api_url = self.config['api_url']
    
    def _load_config(self):
        """Load LLM configuration from JSON file."""
        try:
            config_dir = os.path.dirname(os.path.dirname(__file__))  # Go up to project root
            config_path = os.path.join(config_dir, 'config', 'llm_config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load llm_config.json: {e}, using defaults")
            # Fallback to hardcoded defaults
            self.config = {
                "api_url": "https://api.anthropic.com/v1/messages",
                "models": {"primary": "claude-3-haiku-20240307"},
                "parameters": {
                    "conversation": {"max_tokens": 500, "temperature": 0.8, "timeout": 45},
                    "summary": {"max_tokens": 800, "temperature": 0.3, "timeout": 60}
                }
            }

    async def generate(self, system_prompt, user_message, temperature=None):
        """Generate response with proper system/user message separation"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=data, timeout=self.timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error {response.status}: {error_text}")
                
                result = await response.json()
                return result['content'][0]['text']

    
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
