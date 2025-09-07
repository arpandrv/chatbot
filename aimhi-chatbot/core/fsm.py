from transitions import Machine
from typing import Dict, Optional

# Define conversation states
STATES = [
    'welcome', 
    'support_people', 
    'strengths', 
    'worries', 
    'goals', 
    'llm_conversation'
]

def create_fsm(session_id: str, initial_state: str = 'welcome') -> Dict:
    """Create FSM data with transitions state machine.
    
    Args:
        session_id: Session identifier
        initial_state: Starting state (default: 'welcome')
        
    Returns:
        Dictionary containing FSM machine and session data
    """
    # Create the state machine
    machine = Machine(
        states=STATES,
        initial=initial_state,
        auto_transitions=False,
        ignore_invalid_triggers=True
    )
    
    # Define linear conversation flow
    machine.add_transition('next_step', 'welcome', 'support_people')
    machine.add_transition('next_step', 'support_people', 'strengths')
    machine.add_transition('next_step', 'strengths', 'worries')
    machine.add_transition('next_step', 'worries', 'goals')
    machine.add_transition('next_step', 'goals', 'llm_conversation')
    # No transition from llm_conversation - terminal state
    
    # Return FSM data structure
    return {
        'session_id': session_id,
        'machine': machine,
        'responses': {},  # {state: user_response}
        'attempts': {}    # {state: attempt_count}
    }

# Helper functions for FSM operations

def get_state(fsm_data: Dict) -> str:
    """Get current state."""
    return fsm_data['machine'].state

def advance_state(fsm_data: Dict) -> bool:
    """Move to next state if possible."""
    try:
        fsm_data['machine'].trigger('next_step')
        return True
    except:
        return False

def can_advance(fsm_data: Dict) -> bool:
    """Check if FSM can move to next state."""
    current = get_state(fsm_data)
    return current != 'llm_conversation'

def save_response(fsm_data: Dict, response: str) -> None:
    """Save user response for current state."""
    current = get_state(fsm_data)
    fsm_data['responses'][current] = response

def get_response(fsm_data: Dict, state: str) -> Optional[str]:
    """Get user response for a specific state."""
    return fsm_data['responses'].get(state)

def get_all_responses(fsm_data: Dict) -> Dict[str, str]:
    """Get all user responses."""
    return fsm_data['responses'].copy()

def increment_attempt(fsm_data: Dict) -> None:
    """Increment attempt counter for current state."""
    current = get_state(fsm_data)
    fsm_data['attempts'][current] = fsm_data['attempts'].get(current, 0) + 1

def get_attempt_count(fsm_data: Dict) -> int:
    """Get attempt count for current state."""
    current = get_state(fsm_data)
    return fsm_data['attempts'].get(current, 0)

def should_force_advance(fsm_data: Dict, max_attempts: int = 2) -> bool:
    """Check if we should force advance after multiple attempts."""
    return get_attempt_count(fsm_data) >= max_attempts

def reset_attempts(fsm_data: Dict) -> None:
    """Reset attempt counter for current state."""
    current = get_state(fsm_data)
    fsm_data['attempts'][current] = 0