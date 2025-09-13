"""
FSM tests for core/fsm.py

Comments only — implementation to be added later.

Test setup:
- Import functions: create_fsm, get_state, advance_state, can_advance,
  save_response, get_response, get_all_responses, increment_attempt,
  get_attempt_count, should_force_advance, reset_attempts.

Test cases:
- create_fsm: initial machine in provided initial_state (default 'welcome'); responses and attempts dicts empty.
- can_advance: True for all states except 'llm_conversation'.
- advance_state: walk linear path welcome->support_people->strengths->worries->goals->llm_conversation;
  returns False when attempting to advance from terminal state.
- save/get_response: saves user text for current state; retrievable via get_response and present in get_all_responses copy.
- attempts tracking: increment_attempt increases count for current state; get_attempt_count reflects; reset_attempts sets to 0.
- should_force_advance: returns True when attempts >= max_attempts (default 2) and False otherwise; test custom max_attempts.
- State-specific attempts isolation: attempts for one state don’t leak to next after advance_state + reset_attempts.

Notes:
- These tests should not require any external services or patches.
"""
