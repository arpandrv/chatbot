import os
import aiohttp

class LLMClient:
    def __init__(self, model_name="microsoft/phi-1_5", timeout=6.0):
        self.model = model_name
        self.timeout = timeout
        self.max_tokens = 150
        self.api_key = os.getenv('HUGGINGFACE_API_KEY')
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"

    async def generate(self, prompt, temperature=0.7):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": self.max_tokens,
                "temperature": temperature,
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=data, timeout=self.timeout) as response:
                result = await response.json()
                return result[0]['generated_text']

    def validate_response(self, text):
        # Basic validation
        if not text or len(text) > self.max_tokens:
            return False
        return True
