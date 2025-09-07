import os
import logging
from typing import Dict, List

from llm.client import call_llm

logger = logging.getLogger(__name__)

# System prompt from environment
SYSTEM_PROMPT = os.getenv("LLM_HANDOFF_SYSTEM_PROMPT")
if not SYSTEM_PROMPT:
    raise RuntimeError("LLM_HANDOFF_SYSTEM_PROMPT environment variable not set")

def handle_llm_response(full_conversation: List[Dict]) -> str:
    """Handle user message using LLM with full conversation context"""
    try:
        # Format entire conversation as context
        context_lines = []
        for msg in full_conversation:
            role = "User" if msg["role"] == "user" else "Yarn"
            context_lines.append(f"{role}: {msg['message']}")
        
        context = "\n".join(context_lines)
        response = call_llm(SYSTEM_PROMPT, context)
        
        logger.info(f"LLM response generated successfully")
        return response
        
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise RuntimeError(f"LLM handoff error: {str(e)}")