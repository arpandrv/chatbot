SYSTEM_PROMPT = """You are Yarn, a supportive companion for young Aboriginal and Torres Strait Islander people. 
You help them explore their strengths using the Stay Strong approach.
Never provide medical advice. Keep responses brief and encouraging."""

STEP_PROMPTS = {
    "support_people": "Help the user identify supportive people in their life. Ask about family, friends, Elders, or community members.",
    "strengths": "Help the user recognize what they're good at and proud of.",
    "worries": "Listen supportively to their concerns without trying to solve them.",
    "goals": "Help them identify one achievable goal they'd like to work toward."
}

def format_history(history):
    return "\n".join([f"{turn['role']}: {turn['message']}" for turn in history])

def build_prompt(step, history, user_msg):
    return f"""
{SYSTEM_PROMPT}

Current focus: {STEP_PROMPTS.get(step, "")}

Recent conversation:
{format_history(history[-6:])}

User: {user_msg}
Assistant: [Respond in 1-2 sentences, staying supportive and on-topic]
"""