import asyncio
from llm.client import LLMClient
from llm.prompts import build_prompt
from llm.guardrails import LLMGuardrails
from llm.context import ContextManager

class LLMFallback:
    def __init__(self):
        self.llm_client = LLMClient()
        self.guardrails = LLMGuardrails()
        self.context_manager = ContextManager()

    async def get_reply(self, session_id, current_step, user_msg):
        context = self.context_manager.get_relevant_context(session_id, current_step)
        prompt = build_prompt(current_step, context, user_msg)
        prompt = self.guardrails.pre_process(prompt)

        try:
            response = await self.llm_client.generate(prompt)
            validated_response = self.llm_client.validate_response(response)
            if validated_response:
                processed_response = self.guardrails.post_process(response)
                if processed_response:
                    return processed_response
        except asyncio.TimeoutError:
            return "I'm sorry, I'm taking a little too long to respond. Could you try rephrasing?"
        except Exception as e:
            print(f"LLM Error: {e}")
            return "I'm having a little trouble right now. Let's stick to the main path."

        return "I'm not sure how to respond to that. Let's focus on the current step."
