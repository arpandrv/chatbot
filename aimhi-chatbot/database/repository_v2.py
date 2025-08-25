"""
Enhanced repository module with complete database operations for v2 schema.
Fixes: Atomic transactions, proper error bubbling, CASCADE deletes, WAL mode.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

# Clean database path handling
def get_database_path() -> Path:
    database_url = os.getenv('DATABASE_URL', 'chat_history.db')
    if database_url.startswith('sqlite:///'):
        database_url = database_url[10:]  # Remove sqlite:/// prefix
    
    if not os.path.isabs(database_url):
        database_url = Path(__file__).parent / database_url
    
    return Path(database_url).resolve()

DATABASE_PATH = get_database_path()

@contextmanager
def get_db_connection():
    """Context manager for database connections using connection pool."""
    try:
        # Import the connection pool from app.py
        from app import get_db
        
        # Use the pooled connection
        with get_db() as conn:
            yield conn
            
    except ImportError:
        # Fallback to direct connection if app.py not available (e.g., in tests)
        conn = None
        try:
            conn = sqlite3.connect(str(DATABASE_PATH))
            conn.row_factory = sqlite3.Row
            
            # Apply PRAGMA settings to fallback connection
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL") 
            conn.execute("PRAGMA synchronous = NORMAL")
            
            yield conn
            conn.commit()
        except sqlite3.Error:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

def init_db():
    """Initialize database with v2 schema and performance indexes."""
    # Ensure directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    schema_file = 'schema_v2.sql' if (Path(__file__).parent / 'schema_v2.sql').exists() else 'schema.sql'
    schema_path = Path(__file__).parent / schema_file
    
    with get_db_connection() as conn:
        # Load and execute schema (PRAGMA settings are now in get_db_connection)
        conn.executescript(schema_path.read_text())
        
        # Apply performance indexes
        indexes_path = Path(__file__).parent / 'indexes_v2.sql'
        if indexes_path.exists():
            conn.executescript(indexes_path.read_text())
            logger.info("Performance indexes applied")
        else:
            logger.warning("Performance indexes file not found - database performance may be suboptimal")
    
    logger.info(f"Database initialized with {schema_file} at: {DATABASE_PATH}")

# ============== Utility Functions ==============

def insert_record(conn: sqlite3.Connection, table: str, data: Dict[str, Any]):
    """Utility for clean inserts with SQL injection protection."""
    # Validate table name against whitelist
    ALLOWED_TABLES = {
        'sessions', 'chat_history', 'user_responses', 'risk_detections', 
        'analytics', 'session_summaries', 'intent_classifications', 'system_logs'
    }
    
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table}")
    
    # Validate column names against known schema
    if not all(isinstance(key, str) and key.replace('_', '').isalnum() for key in data.keys()):
        raise ValueError("Invalid column names detected")
    
    columns = ', '.join(f'"{key}"' for key in data.keys())  # Quote column names
    placeholders = ', '.join('?' * len(data))
    
    # Use parameterized query with quoted identifiers
    query = f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})'
    conn.execute(query, tuple(data.values()))

# ============== Session Management ==============

def create_session(session_id: str, fsm_state: str = 'welcome'):
    """Create a new session. Raises on error."""
    with get_db_connection() as conn:
        conn.execute('INSERT OR IGNORE INTO sessions (session_id, fsm_state) VALUES (?, ?)', 
                    (session_id, fsm_state))

def get_session_data(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data. Returns None if not found."""
    with get_db_connection() as conn:
        result = conn.execute('''
            SELECT session_id, fsm_state, created_at, last_activity, completed
            FROM sessions WHERE session_id = ?
        ''', (session_id,)).fetchone()
    return dict(result) if result else None

def update_session_state(session_id: str, fsm_state: str):
    """Update FSM state. Raises on error."""
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE sessions 
            SET fsm_state = ?, last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (fsm_state, session_id))

def mark_session_completed(session_id: str):
    """Mark session as completed. Raises on error."""
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE sessions 
            SET completed = TRUE, completion_time = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (session_id,))

# ============== Chat History ==============

def save_message(session_id: str, role: str, message: str):
    """Save message. Raises on error."""
    with get_db_connection() as conn:
        # Ensure session exists and save message atomically
        conn.execute('INSERT OR IGNORE INTO sessions (session_id) VALUES (?)', (session_id,))
        conn.execute('INSERT INTO chat_history (session_id, role, message) VALUES (?, ?, ?)',
                    (session_id, role, message))
        conn.execute('UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?',
                    (session_id,))

def get_history(session_id: str, limit: int = 6) -> List[sqlite3.Row]:
    """Get chat history. Returns empty list if none found."""
    with get_db_connection() as conn:
        return conn.execute('''
            SELECT role, message FROM chat_history 
            WHERE session_id = ? 
            ORDER BY ts DESC LIMIT ?
        ''', (session_id, limit)).fetchall()

# ============== User Responses ==============

def save_user_response(session_id: str, step: str, response: str, attempt_count: int = 0):
    """Save user response. Raises on error."""
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO user_responses (session_id, step, response, attempt_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id, step) 
            DO UPDATE SET 
                response = excluded.response,
                attempt_count = excluded.attempt_count,
                updated_at = CURRENT_TIMESTAMP
        ''', (session_id, step, response, attempt_count))

def get_user_responses(session_id: str) -> Dict[str, str]:
    """Get all user responses for session."""
    with get_db_connection() as conn:
        responses = conn.execute('''
            SELECT step, response FROM user_responses 
            WHERE session_id = ?
        ''', (session_id,)).fetchall()
    return {row['step']: row['response'] for row in responses if row['response']}

def update_attempt_count(session_id: str, step: str) -> int:
    """Increment attempt count atomically. Returns new count."""
    with get_db_connection() as conn:
        # Atomic upsert to avoid race conditions
        conn.execute('''
            INSERT INTO user_responses (session_id, step, attempt_count)
            VALUES (?, ?, 1)
            ON CONFLICT(session_id, step) 
            DO UPDATE SET attempt_count = attempt_count + 1
        ''', (session_id, step))
        
        result = conn.execute('''
            SELECT attempt_count FROM user_responses 
            WHERE session_id = ? AND step = ?
        ''', (session_id, step)).fetchone()
        
    return result['attempt_count'] if result else 0

# ============== Risk Detection ==============

def save_analytics_event_in_transaction(conn: sqlite3.Connection, event_type: str, event_data: Optional[Dict] = None):
    """Save analytics event within existing transaction."""
    insert_record(conn, 'analytics', {
        'event_type': event_type,
        'event_data': json.dumps(event_data) if event_data else None
    })

def save_risk_detection(session_id: str, trigger_phrase: str, user_message: str):
    """Save risk detection atomically with analytics. Raises on error."""
    with get_db_connection() as conn:
        # FIXED: Both operations in same transaction for atomicity
        insert_record(conn, 'risk_detections', {
            'session_id': session_id,
            'trigger_phrase': trigger_phrase,
            'user_message': user_message
        })
        
        # Analytics event in same transaction
        save_analytics_event_in_transaction(conn, 'risk_triggered', {'session_id': session_id})

def get_risk_detections(session_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get risk detections."""
    with get_db_connection() as conn:
        if session_id:
            results = conn.execute('''
                SELECT * FROM risk_detections 
                WHERE session_id = ? 
                ORDER BY detected_at DESC LIMIT ?
            ''', (session_id, limit)).fetchall()
        else:
            results = conn.execute('''
                SELECT * FROM risk_detections 
                ORDER BY detected_at DESC LIMIT ?
            ''', (limit,)).fetchall()
    
    return [dict(row) for row in results]

# ============== Session Summaries ==============

def save_session_summary(session_id: str, summary_type: str, summary_data: Dict[str, Any]):
    """Save session summary. Raises on error."""
    with get_db_connection() as conn:
        insert_record(conn, 'session_summaries', {
            'session_id': session_id,
            'summary_type': summary_type,
            'summary_data': json.dumps(summary_data)
        })

def get_latest_summary(session_id: str, summary_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get latest summary for session."""
    with get_db_connection() as conn:
        if summary_type:
            result = conn.execute('''
                SELECT summary_data FROM session_summaries 
                WHERE session_id = ? AND summary_type = ?
                ORDER BY generated_at DESC LIMIT 1
            ''', (session_id, summary_type)).fetchone()
        else:
            result = conn.execute('''
                SELECT summary_data FROM session_summaries 
                WHERE session_id = ?
                ORDER BY generated_at DESC LIMIT 1
            ''', (session_id,)).fetchone()
    
    return json.loads(result['summary_data']) if result else None

# ============== Analytics ==============

def save_analytics_event(event_type: str, event_data: Optional[Dict] = None):
    """Save analytics event. Raises on error."""
    with get_db_connection() as conn:
        save_analytics_event_in_transaction(conn, event_type, event_data)

def get_analytics_summary(days: int = 7) -> Dict[str, Any]:
    """Get analytics summary for last N days."""
    with get_db_connection() as conn:
        # FIXED: Proper date filtering
        events = conn.execute('''
            SELECT event_type, COUNT(*) as count
            FROM analytics 
            WHERE timestamp > datetime('now', printf('-%d days', ?))
            GROUP BY event_type
        ''', (days,)).fetchall()
        
        completion_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_sessions,
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed,
                ROUND(100.0 * SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as completion_rate
            FROM sessions
            WHERE created_at > datetime('now', printf('-%d days', ?))
        ''', (days,)).fetchone()
        
    return {
        'event_counts': {row['event_type']: row['count'] for row in events},
        'completion_stats': dict(completion_stats) if completion_stats else {}
    }

# ============== Intent Classification Tracking ==============

def save_intent_classification(
    session_id: str, 
    user_message: str, 
    intent: str, 
    confidence: float,
    method: str,
    fsm_state: Optional[str] = None,
    inference_time_ms: Optional[int] = None
):
    """Save intent classification result. Raises on error."""
    with get_db_connection() as conn:
        insert_record(conn, 'intent_classifications', {
            'session_id': session_id,
            'user_message': user_message,
            'classified_intent': intent,
            'confidence': confidence,
            'method': method,
            'fsm_state': fsm_state,
            'inference_time_ms': inference_time_ms
        })

# ============== System Logging ==============

def save_system_log(
    log_level: str,
    component: str,
    message: str,
    session_id: Optional[str] = None,
    error_trace: Optional[str] = None
):
    """Save system log entry. Raises on error."""
    with get_db_connection() as conn:
        insert_record(conn, 'system_logs', {
            'log_level': log_level,
            'component': component,
            'message': message,
            'session_id': session_id,
            'error_trace': error_trace
        })

# ============== Data Cleanup ==============

def cleanup_old_sessions(days: int = 30) -> int:
    """
    Clean up old completed sessions using CASCADE deletes.
    NOTE: Requires ON DELETE CASCADE in schema_v2.sql foreign keys.
    """
    with get_db_connection() as conn:
        # FIXED: Single query with CASCADE handling the rest
        cursor = conn.execute('''
            DELETE FROM sessions
            WHERE created_at < datetime('now', printf('-%d days', ?))
              AND completed = 1
        ''', (days,))
        
        count = cursor.rowcount
    
    if count > 0:
        logger.info(f"Cleaned up {count} old sessions")
    return count

if __name__ == "__main__":
    init_db()