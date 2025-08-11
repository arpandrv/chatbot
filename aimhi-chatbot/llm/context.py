from database.repository import get_history

class ContextManager:
    def __init__(self, max_turns=6, max_tokens=1024):
        self.max_turns = max_turns
        self.max_tokens = max_tokens

    def get_relevant_context(self, session_id, current_step):
        history = get_history(session_id, self.max_turns)
        # In a real implementation, you might do more here to select the most relevant turns
        # based on the current step, but for now, we'll just return the latest turns.
        return history
