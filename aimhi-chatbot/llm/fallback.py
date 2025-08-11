import requests
from llm.prompts import build_prompt
from llm.guardrails import LLMGuardrails
from llm.context import ContextManager
import os

class LLMFallback:
    def __init__(self):
        self.guardrails = LLMGuardrails()
        self.context_manager = ContextManager()
        self.api_key = os.getenv('HUGGINGFACE_API_KEY')
        self.model = os.getenv('LLM_MODEL', 'microsoft/DialoGPT-small')
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"
        self.timeout = float(os.getenv('LLM_TIMEOUT', '6.0'))
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', '100'))
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))

    def get_reply(self, session_id, current_step, user_msg):
        # Get context and build prompt
        context = self.context_manager.get_relevant_context(session_id, current_step)
        prompt = build_prompt(current_step, context, user_msg)
        prompt = self.guardrails.pre_process(prompt)

        try:
            # Make synchronous API call to Hugging Face
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "return_full_text": False
                }
            }
            
            response = requests.post(
                self.api_url, 
                headers=headers, 
                json=data, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    generated_text = result[0].get('generated_text', '')
                    # Apply guardrails
                    processed_response = self.guardrails.post_process(generated_text)
                    if processed_response:
                        return processed_response
            
        except requests.Timeout:
            return "I'm sorry, I'm taking a little too long to respond. Could you try rephrasing?"
        except Exception as e:
            print(f"LLM Error: {e}")
            return "I'm having a little trouble right now. Let's stick to the main path."

        return "I'm not sure how to respond to that. Let's focus on the current step."
