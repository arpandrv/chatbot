# Tests for database/repository functions (Supabase repository layer)
#
# Strategy:
# - Patch database.repository.supabase_service with a chainable fake that records calls and returns pre-baked data.
# - Patch database.repository.get_session for ownership checks in message/analytics functions.
# - No network or real DB.
#
# Test cases:
# - create_session: inserts row and returns session_id string from result.data[0]['session_id']; logs on success/failure.
# - get_session: builds correct select/filters and returns first row or None.
# - update_session_state: builds update with provided fields and returns True when result.data non-empty.
# - save_message: when get_session returns None -> returns None; when owned -> inserts and returns message id.
# - get_chat_history: requires ownership; returns list (possibly empty) ordered asc limited by arg.
# - accept_response: verifies message exists and matches session/step; unmarks previous finals for step; marks target id and returns True.
# - get_final_responses_map: returns dict of step->message only for rows with fsm_step set.
# - record_risk_detection / record_intent_classification: require ownership; insert and return new id.
# - get_user_sessions: select filtered by user_id and limited; returns list.
# - delete_old_sessions: deletes by last_activity < cutoff and returns count (just length of result.data).
# - Legacy aliases insert_message/get_messages/record_intent call through to primary implementations.
#
# Notes:
# - The fake supabase_service should mimic: table(name) -> self; methods select/insert/update/delete/eq/lt/order/limit return self;
#   execute() returns an object with a .data attribute (list) per test scenario.
# - Assert filters passed (e.g., eq/lt args) by capturing calls in the fake.

