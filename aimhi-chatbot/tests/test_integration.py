"""
High-level integration tests (mocked) for main flows

Comments only — implementation to be added later.

Scope:
- Exercise the Flask API endpoints together with router behavior, but mock all external boundaries
  (Supabase client, NLP calls, LLMs). Focus on data flow correctness and sequencing.

Fixtures/Setup:
- Flask app test_client from aimhi_chatbot.app.
- Patch auth to inject a fixed user_id for protected routes.
- Patch repository layer to simulate session create/read/update and chat_history mutations (in-memory list).
- Patch router.route_message to emulate FSM advancement across a few calls with deterministic replies.
- Patch config.supabase_client.test_connection as needed.

Test scenarios:
- Full structured chat path:
  1) POST /sessions -> get session_id.
  2) POST /api/chat -> welcome response; verify repository.save_message called for user+bot.
  3) Send messages to transition through support_people, strengths, worries, goals -> asserts state updates persisted.
  4) Verify GET /sessions/<id>/messages returns all messages in order.
- Risk detection branch:
  - Mock router.contains_risk True -> /api/chat returns crisis text and records risk detection; no FSM advancement.
- Accept final response:
  - After some bot messages with fsm_step, POST /sessions/<id>/accept marks a message id as final; verify accept_response called.

Notes:
- Keep tests hermetic (no network). Use monkeypatch/unittest.mock liberally.
"""
