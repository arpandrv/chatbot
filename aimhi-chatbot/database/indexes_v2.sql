-- Performance indexes for common queries
-- Add these to your schema_v2.sql or run separately

-- Session lookups (most common operation)
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_sessions_fsm_state ON sessions(fsm_state);

-- Chat history queries
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_ts ON chat_history(ts DESC);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_ts ON chat_history(session_id, ts DESC);

-- User responses for FSM state reconstruction  
CREATE INDEX IF NOT EXISTS idx_user_responses_session_id ON user_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_user_responses_step ON user_responses(step);

-- Analytics queries
CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp DESC);

-- Risk detection queries
CREATE INDEX IF NOT EXISTS idx_risk_detections_session_id ON risk_detections(session_id);
CREATE INDEX IF NOT EXISTS idx_risk_detections_detected_at ON risk_detections(detected_at DESC);

-- Intent classification performance tracking
CREATE INDEX IF NOT EXISTS idx_intent_classifications_session_id ON intent_classifications(session_id);
CREATE INDEX IF NOT EXISTS idx_intent_classifications_method ON intent_classifications(method);
CREATE INDEX IF NOT EXISTS idx_intent_classifications_confidence ON intent_classifications(confidence);

-- System logs for debugging
CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component);
CREATE INDEX IF NOT EXISTS idx_system_logs_log_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp DESC);