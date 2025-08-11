from transitions import Machine

class ChatBotFSM:
    states = ['welcome', 'support_people', 'strengths', 'worries', 'goals', 'summary']

    def __init__(self, session_id):
        self.session_id = session_id
        self.machine = Machine(model=self, states=ChatBotFSM.states, initial='welcome')

        self.machine.add_transition(trigger='next_step', source='welcome', dest='support_people')
        self.machine.add_transition(trigger='next_step', source='support_people', dest='strengths')
        self.machine.add_transition(trigger='next_step', source='strengths', dest='worries')
        self.machine.add_transition(trigger='next_step', source='worries', dest='goals')
        self.machine.add_transition(trigger='next_step', source='goals', dest='summary')
        
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
    
    def save_response(self, response):
        """Save user response for current state"""
        if self.state in self.responses:
            self.responses[self.state] = response
    
    def get_response(self, state):
        """Get user response for a specific state"""
        return self.responses.get(state, None)
    
    def get_all_responses(self):
        """Get all user responses"""
        return self.responses
    
    def increment_attempt(self):
        """Increment attempt counter for current state"""
        if self.state in self.attempts:
            self.attempts[self.state] += 1
    
    def get_attempt_count(self):
        """Get attempt count for current state"""
        return self.attempts.get(self.state, 0)
    
    def should_offer_choice(self):
        """Check if we should offer user choice to move on"""
        return self.get_attempt_count() == 2  # After second failed attempt
    
    def should_force_advance(self):
        """Check if we should force advance after multiple attempts"""
        return self.get_attempt_count() >= 3  # After third failed attempt
