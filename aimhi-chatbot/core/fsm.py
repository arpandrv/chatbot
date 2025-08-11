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
