# chatbot/aimhi-chatbot/core/fsm.py

from transitions import Machine

class ChatBotFSM:
    # Define all states in order
    states = [
        'welcome', 
        'support_people', 
        'strengths', 
        'worries', 
        'goals', 
        'summary',
        'llm_conversation'
    ]

    def __init__(self, session_id: str, initial_state: str = 'welcome'):
        self.session_id = session_id
        
        # Create the state machine with simple forward-only flow
        self.machine = Machine(
            model=self, 
            states=ChatBotFSM.states, 
            initial=initial_state,  # Start from provided state
            auto_transitions=False,  # No automatic transitions
            ignore_invalid_triggers=True  # Don't crash on invalid transitions
        )

        # Define ONLY forward transitions - one way flow
        self.machine.add_transition(trigger='next_step', source='welcome', dest='support_people')
        self.machine.add_transition(trigger='next_step', source='support_people', dest='strengths')
        self.machine.add_transition(trigger='next_step', source='strengths', dest='worries')
        self.machine.add_transition(trigger='next_step', source='worries', dest='goals')
        self.machine.add_transition(trigger='next_step', source='goals', dest='summary')
        self.machine.add_transition(trigger='start_llm_chat', source='summary', dest='llm_conversation')
        # No transition from llm_conversation - it's the final state

        # Store user responses for each step
        self.responses = {
            'support_people': None,
            'strengths': None,
            'worries': None,
            'goals': None
        }
        
        # Track attempts for progressive fallback
        self.attempts = {
            'support_people': 0,
            'strengths': 0,
            'worries': 0,
            'goals': 0
        }
    
    def save_response(self, response: str):
        """Save the user's response for the current step"""
        if self.state in self.responses:
            self.responses[self.state] = response
    
    def get_response(self, state: str) -> str | None:
        """Get the user's response for a specific step"""
        return self.responses.get(state, None)
    
    def get_all_responses(self) -> dict:
        """Get all user responses"""
        return self.responses
    
    def increment_attempt(self):
        """Increment attempt counter for current step"""
        if self.state in self.attempts:
            self.attempts[self.state] += 1
    
    def get_attempt_count(self) -> int:
        """Get attempt count for current step"""
        return self.attempts.get(self.state, 0)
    
    def should_advance(self) -> bool:
        """Check if we should force advance after multiple attempts"""
        return self.get_attempt_count() >= 2
    
    def reset_attempts(self):
        """Reset attempt counter for current step"""
        if self.state in self.attempts:
            self.attempts[self.state] = 0
    
    def can_advance(self) -> bool:
        """Check if FSM can move to next state"""
        # Can't advance from final states
        if self.state in ['llm_conversation']:
            return False
        # Can advance from summary only via start_llm_chat
        if self.state == 'summary':
            return True  # But needs different trigger
        # All other states can advance
        return True