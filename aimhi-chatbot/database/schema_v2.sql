-- AIMhi-Y Chatbot Database Schema v2 with CASCADE deletes
-- Complete schema with all necessary tables for production use

-- 1. Sessions table for persistent session management
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  fsm_state TEXT NOT NULL DEFAULT 'welcome' CHECK(fsm_state IN ('welcome','support_people','strengths','worries','goals','summary','llm_conversation')),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed BOOLEAN DEFAULT FALSE,
  completion_time DATETIME
);

CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_sessions_completed ON sessions(completed);

-- 2. Chat history table with CASCADE delete
CREATE TABLE IF NOT EXISTS chat_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT CHECK(role IN ('user','bot')) NOT NULL,
  message TEXT NOT NULL,
  ts DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chat_session_ts ON chat_history(session_id, ts);

-- 3. User responses table with CASCADE delete
CREATE TABLE IF NOT EXISTS user_responses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  step TEXT CHECK(step IN ('support_people','strengths','worries','goals')) NOT NULL,
  response TEXT,
  attempt_count INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
  UNIQUE(session_id, step)
);

CREATE INDEX IF NOT EXISTS idx_user_responses_session ON user_responses(session_id);

-- 4. Risk detections table with CASCADE delete
CREATE TABLE IF NOT EXISTS risk_detections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  trigger_phrase TEXT NOT NULL,
  user_message TEXT NOT NULL,
  detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  resources_shown BOOLEAN DEFAULT TRUE,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_risk_detections_session ON risk_detections(session_id);
CREATE INDEX IF NOT EXISTS idx_risk_detections_date ON risk_detections(detected_at);

-- 5. Session summaries table with CASCADE delete
CREATE TABLE IF NOT EXISTS session_summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  summary_type TEXT CHECK(summary_type IN ('partial','complete','llm_context')) NOT NULL,
  summary_data TEXT NOT NULL, -- JSON format
  generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_summaries_session ON session_summaries(session_id);
CREATE INDEX IF NOT EXISTS idx_summaries_type ON session_summaries(summary_type);

-- 6. Analytics table (no CASCADE - we want to keep aggregate stats)
CREATE TABLE IF NOT EXISTS analytics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL CHECK(event_type IN (
    'session_started',
    'session_completed', 
    'step_completed',
    'risk_triggered',
    'llm_fallback_used',
    'distilbert_used',
    'rule_based_used',
    'llm_turn_completed'
  )),
  event_data TEXT, -- JSON format for flexibility
  session_count INTEGER DEFAULT 1,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp);
CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics(event_type);

-- 7. Intent classifications table with CASCADE delete
CREATE TABLE IF NOT EXISTS intent_classifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  user_message TEXT NOT NULL,
  classified_intent TEXT NOT NULL,
  confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
  method TEXT CHECK(method IN ('distilbert','rule_based','hybrid')) NOT NULL,
  fsm_state TEXT,
  inference_time_ms INTEGER CHECK(inference_time_ms >= 0),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_intent_session ON intent_classifications(session_id);
CREATE INDEX IF NOT EXISTS idx_intent_created ON intent_classifications(created_at);

-- 8. System logs table with optional CASCADE delete
CREATE TABLE IF NOT EXISTS system_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  log_level TEXT CHECK(log_level IN ('DEBUG','INFO','WARNING','ERROR','CRITICAL')) NOT NULL,
  component TEXT NOT NULL,
  message TEXT NOT NULL,
  session_id TEXT,
  error_trace TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_logs_session ON system_logs(session_id);

-- Performance indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_user_responses_session_step ON user_responses(session_id, step);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_role ON chat_history(session_id, role);
CREATE INDEX IF NOT EXISTS idx_analytics_event_timestamp ON analytics(event_type, timestamp);

-- Data retention views for monitoring
CREATE VIEW IF NOT EXISTS sessions_to_cleanup AS
SELECT session_id, created_at 
FROM sessions 
WHERE created_at < datetime('now', '-30 days')
AND completed = TRUE;

-- Analytics aggregation view
CREATE VIEW IF NOT EXISTS daily_analytics AS
SELECT 
  date(timestamp) as date,
  event_type,
  COUNT(*) as event_count,
  SUM(session_count) as total_sessions
FROM analytics
GROUP BY date(timestamp), event_type
ORDER BY date DESC, event_type;

-- Session completion rate view
CREATE VIEW IF NOT EXISTS session_completion_stats AS
SELECT 
  date(created_at) as date,
  COUNT(*) as total_sessions,
  SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) as completed_sessions,
  ROUND(100.0 * SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) / COUNT(*), 2) as completion_rate
FROM sessions
GROUP BY date(created_at)
ORDER BY date DESC;