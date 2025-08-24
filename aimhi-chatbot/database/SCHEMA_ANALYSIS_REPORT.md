# Database Schema Analysis Report

## Current Schema Status

### Existing Tables
The database currently has only **ONE** table:

#### `chat_history` Table
```sql
CREATE TABLE IF NOT EXISTS chat_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT CHECK(role IN ('user','bot')) NOT NULL,
  message TEXT NOT NULL,
  ts DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_session_ts ON chat_history(session_id, ts);
```

## Missing Schema Elements

Based on the codebase analysis, several important schema elements are **MISSING** that should be added for a complete system:

### 1. **Sessions Table** (CRITICAL)
Currently, sessions are only stored in memory (`sessions = {}` in `core/session.py`). This means:
- Sessions are lost on server restart
- No persistence of FSM state
- Cannot resume conversations

**Recommended Schema:**
```sql
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  fsm_state TEXT NOT NULL DEFAULT 'welcome',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed BOOLEAN DEFAULT FALSE,
  completion_time DATETIME
);

CREATE INDEX idx_sessions_last_activity ON sessions(last_activity);
```

### 2. **User Responses Table** (CRITICAL)
The FSM stores responses in memory (`self.responses` in `core/fsm.py`). These should be persisted:

**Recommended Schema:**
```sql
CREATE TABLE IF NOT EXISTS user_responses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  step TEXT CHECK(step IN ('support_people','strengths','worries','goals')) NOT NULL,
  response TEXT,
  attempt_count INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id),
  UNIQUE(session_id, step)
);

CREATE INDEX idx_user_responses_session ON user_responses(session_id);
```

### 3. **Risk Detections Table** (IMPORTANT)
For tracking and monitoring risk language detections:

**Recommended Schema:**
```sql
CREATE TABLE IF NOT EXISTS risk_detections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  trigger_phrase TEXT NOT NULL,
  user_message TEXT NOT NULL,
  detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  resources_shown BOOLEAN DEFAULT TRUE,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_risk_detections_session ON risk_detections(session_id);
CREATE INDEX idx_risk_detections_date ON risk_detections(detected_at);
```

### 4. **Session Summaries Table** (IMPORTANT)
For storing generated summaries from `llm/summary_generator.py`:

**Recommended Schema:**
```sql
CREATE TABLE IF NOT EXISTS session_summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  summary_type TEXT CHECK(summary_type IN ('partial','complete')) NOT NULL,
  summary_data TEXT NOT NULL, -- JSON format
  generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_summaries_session ON session_summaries(session_id);
```

### 5. **Analytics Table** (NICE TO HAVE)
For anonymous usage metrics mentioned in PRD:

**Recommended Schema:**
```sql
CREATE TABLE IF NOT EXISTS analytics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  event_data TEXT, -- JSON format for flexibility
  session_count INTEGER DEFAULT 0,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analytics_timestamp ON analytics(timestamp);
CREATE INDEX idx_analytics_event_type ON analytics(event_type);
```

### 6. **Intent Classifications Table** (OPTIONAL)
For tracking intent classification performance:

**Recommended Schema:**
```sql
CREATE TABLE IF NOT EXISTS intent_classifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  user_message TEXT NOT NULL,
  classified_intent TEXT NOT NULL,
  confidence REAL,
  method TEXT CHECK(method IN ('distilbert','rule_based','hybrid')) NOT NULL,
  fsm_state TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_intent_session ON intent_classifications(session_id);
```

## Implementation Priority

### Phase 1 - Critical (Immediate)
1. **Sessions Table** - Essential for persistence
2. **User Responses Table** - Core functionality

### Phase 2 - Important (Next Sprint)
3. **Risk Detections Table** - Safety monitoring
4. **Session Summaries Table** - LLM integration

### Phase 3 - Nice to Have (Future)
5. **Analytics Table** - Usage insights
6. **Intent Classifications Table** - Model performance

## Migration Strategy

1. Create new `schema_v2.sql` with all tables
2. Update `repository.py` with new functions:
   - `save_session()`
   - `get_session_data()`
   - `save_user_response()`
   - `save_risk_detection()`
   - `save_summary()`
   - `save_analytics_event()`

3. Modify existing code:
   - `core/session.py` - Use database instead of memory
   - `core/fsm.py` - Persist state changes
   - `core/router.py` - Save risk detections

## Data Privacy Considerations

- All tables maintain **anonymous session IDs** (no PII)
- Consider adding data retention policies:
  - Auto-delete sessions older than 30 days
  - Aggregate analytics data weekly
  - Remove chat history after session completion (configurable)

## Performance Optimizations

- All foreign keys and frequently queried columns are indexed
- Consider partitioning `chat_history` by date for large deployments
- Implement connection pooling in `repository.py`
- Add database backup strategy

## Recommended Next Steps

1. **Immediate Action**: Add Sessions and User Responses tables
2. **Update Repository**: Extend `repository.py` with new CRUD operations
3. **Refactor Session Management**: Move from memory to database
4. **Add Migration Script**: Create database migration tool
5. **Test Thoroughly**: Ensure backward compatibility

## Conclusion

The current schema is **INSUFFICIENT** for production use. Only basic chat history is stored, while critical session state, user responses, and safety tracking are missing. Implementing the recommended schema additions will provide:

- **Persistence**: Conversations survive server restarts
- **Safety**: Track and monitor risk detections
- **Analytics**: Measure system performance
- **Reliability**: Proper data management and recovery

The system is currently operating with significant data loss risk and limited monitoring capabilities.