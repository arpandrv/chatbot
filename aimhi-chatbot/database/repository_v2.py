"""
Enhanced repository module with complete database operations for v2 schema.
Provides persistence for sessions, responses, risk tracking, and analytics.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Database configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
default_db_path = os.path.join(script_dir, 'chat_history.db')
database_url = os.getenv('DATABASE_URL', default_db_path)

if database_url.startswith('sqlite:///'):
    DATABASE_URL = database_url.replace('sqlite:///', '')
    if not os.path.isabs(DATABASE_URL):
        DATABASE_URL = os.path.join(os.path.dirname(script_dir), DATABASE_URL)
else:
    DATABASE_URL = database_url


def get_db_connection():
    """Get database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with v2 schema."""
    try:
        # Ensure database directory exists
        db_dir = os.path.dirname(DATABASE_URL)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        conn = get_db_connection()
        
        # Check if we need to use v2 schema
        schema_file = 'schema_v2.sql' if os.path.exists(os.path.join(script_dir, 'schema_v2.sql')) else 'schema.sql'
        schema_path = os.path.join(script_dir, schema_file)
        
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        
        conn.close()
        logger.info(f"Database initialized with {schema_file} at: {DATABASE_URL}")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


# ============== Session Management ==============

def create_session(session_id: str, fsm_state: str = 'welcome') -> bool:
    """Create a new session in the database."""
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT OR IGNORE INTO sessions (session_id, fsm_state) 
            VALUES (?, ?)
        ''', (session_id, fsm_state))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return False


def get_session_data(session_id: str) -> Optional[Dict]:
    """Retrieve session data from database."""
    try:
        conn = get_db_connection()
        session = conn.execute('''
            SELECT session_id, fsm_state, created_at, last_activity, completed
            FROM sessions WHERE session_id = ?
        ''', (session_id,)).fetchone()
        conn.close()
        
        if session:
            return dict(session)
        return None
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        return None


def update_session_state(session_id: str, fsm_state: str) -> bool:
    """Update FSM state for a session."""
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE sessions 
            SET fsm_state = ?, last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (fsm_state, session_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating session state: {e}")
        return False


def mark_session_completed(session_id: str) -> bool:
    """Mark a session as completed."""
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE sessions 
            SET completed = TRUE, completion_time = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (session_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error marking session completed: {e}")
        return False


# ============== Chat History (existing) ==============

def save_message(session_id: str, role: str, message: str):
    """Save a chat message (existing function, enhanced)."""
    try:
        conn = get_db_connection()
        
        # Ensure session exists
        conn.execute('INSERT OR IGNORE INTO sessions (session_id) VALUES (?)', (session_id,))
        
        # Save message
        conn.execute('''
            INSERT INTO chat_history (session_id, role, message) 
            VALUES (?, ?, ?)
        ''', (session_id, role, message))
        
        # Update session last activity
        conn.execute('''
            UPDATE sessions SET last_activity = CURRENT_TIMESTAMP 
            WHERE session_id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving message: {e}")


def get_history(session_id: str, limit: int = 6) -> List[sqlite3.Row]:
    """Get chat history (existing function)."""
    conn = get_db_connection()
    history = conn.execute('''
        SELECT role, message FROM chat_history 
        WHERE session_id = ? 
        ORDER BY ts DESC LIMIT ?
    ''', (session_id, limit)).fetchall()
    conn.close()
    return history


# ============== User Responses ==============

def save_user_response(session_id: str, step: str, response: str, attempt_count: int = 0) -> bool:
    """Save or update user response for a specific FSM step."""
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO user_responses (session_id, step, response, attempt_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id, step) 
            DO UPDATE SET 
                response = excluded.response,
                attempt_count = excluded.attempt_count,
                updated_at = CURRENT_TIMESTAMP
        ''', (session_id, step, response, attempt_count))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving user response: {e}")
        return False


def get_user_responses(session_id: str) -> Dict[str, str]:
    """Get all user responses for a session."""
    try:
        conn = get_db_connection()
        responses = conn.execute('''
            SELECT step, response FROM user_responses 
            WHERE session_id = ?
        ''', (session_id,)).fetchall()
        conn.close()
        
        return {row['step']: row['response'] for row in responses}
    except Exception as e:
        logger.error(f"Error getting user responses: {e}")
        return {}


def update_attempt_count(session_id: str, step: str) -> int:
    """Increment and return attempt count for a step."""
    try:
        conn = get_db_connection()
        
        # Get current count
        result = conn.execute('''
            SELECT attempt_count FROM user_responses 
            WHERE session_id = ? AND step = ?
        ''', (session_id, step)).fetchone()
        
        current_count = result['attempt_count'] if result else 0
        new_count = current_count + 1
        
        # Update or insert
        conn.execute('''
            INSERT INTO user_responses (session_id, step, attempt_count)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id, step) 
            DO UPDATE SET attempt_count = excluded.attempt_count
        ''', (session_id, step, new_count))
        
        conn.commit()
        conn.close()
        return new_count
    except Exception as e:
        logger.error(f"Error updating attempt count: {e}")
        return 0


# ============== Risk Detection ==============

def save_risk_detection(session_id: str, trigger_phrase: str, user_message: str) -> bool:
    """Save a risk detection event."""
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO risk_detections (session_id, trigger_phrase, user_message)
            VALUES (?, ?, ?)
        ''', (session_id, trigger_phrase, user_message))
        conn.commit()
        conn.close()
        
        # Also log as analytics event
        save_analytics_event('risk_triggered', {'session_id': session_id})
        return True
    except Exception as e:
        logger.error(f"Error saving risk detection: {e}")
        return False


def get_risk_detections(session_id: str = None, limit: int = 100) -> List[Dict]:
    """Get risk detections, optionally filtered by session."""
    try:
        conn = get_db_connection()
        
        if session_id:
            query = '''
                SELECT * FROM risk_detections 
                WHERE session_id = ? 
                ORDER BY detected_at DESC LIMIT ?
            '''
            results = conn.execute(query, (session_id, limit)).fetchall()
        else:
            query = '''
                SELECT * FROM risk_detections 
                ORDER BY detected_at DESC LIMIT ?
            '''
            results = conn.execute(query, (limit,)).fetchall()
        
        conn.close()
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error getting risk detections: {e}")
        return []


# ============== Session Summaries ==============

def save_session_summary(session_id: str, summary_type: str, summary_data: Dict) -> bool:
    """Save a session summary (for LLM context or completion)."""
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO session_summaries (session_id, summary_type, summary_data)
            VALUES (?, ?, ?)
        ''', (session_id, summary_type, json.dumps(summary_data)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving session summary: {e}")
        return False


def get_latest_summary(session_id: str, summary_type: str = None) -> Optional[Dict]:
    """Get the latest summary for a session."""
    try:
        conn = get_db_connection()
        
        if summary_type:
            query = '''
                SELECT summary_data FROM session_summaries 
                WHERE session_id = ? AND summary_type = ?
                ORDER BY generated_at DESC LIMIT 1
            '''
            result = conn.execute(query, (session_id, summary_type)).fetchone()
        else:
            query = '''
                SELECT summary_data FROM session_summaries 
                WHERE session_id = ?
                ORDER BY generated_at DESC LIMIT 1
            '''
            result = conn.execute(query, (session_id,)).fetchone()
        
        conn.close()
        
        if result:
            return json.loads(result['summary_data'])
        return None
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return None


# ============== Analytics ==============

def save_analytics_event(event_type: str, event_data: Dict = None) -> bool:
    """Save an analytics event."""
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO analytics (event_type, event_data)
            VALUES (?, ?)
        ''', (event_type, json.dumps(event_data) if event_data else None))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving analytics event: {e}")
        return False


def get_analytics_summary(days: int = 7) -> Dict:
    """Get analytics summary for the last N days."""
    try:
        conn = get_db_connection()
        
        # Get event counts
        events = conn.execute('''
            SELECT event_type, COUNT(*) as count
            FROM analytics 
            WHERE timestamp > datetime('now', ? || ' days')
            GROUP BY event_type
        ''', (-days,)).fetchall()
        
        # Get completion stats
        completion_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_sessions,
                SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) as completed,
                ROUND(100.0 * SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) / COUNT(*), 2) as completion_rate
            FROM sessions
            WHERE created_at > datetime('now', ? || ' days')
        ''', (-days,)).fetchone()
        
        conn.close()
        
        return {
            'event_counts': {row['event_type']: row['count'] for row in events},
            'completion_stats': dict(completion_stats) if completion_stats else {}
        }
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        return {}


# ============== Intent Classification Tracking ==============

def save_intent_classification(
    session_id: str, 
    user_message: str, 
    intent: str, 
    confidence: float,
    method: str,
    fsm_state: str = None,
    inference_time_ms: int = None
) -> bool:
    """Save intent classification result for performance tracking."""
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO intent_classifications 
            (session_id, user_message, classified_intent, confidence, method, fsm_state, inference_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, user_message, intent, confidence, method, fsm_state, inference_time_ms))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving intent classification: {e}")
        return False


# ============== System Logging ==============

def save_system_log(
    log_level: str,
    component: str,
    message: str,
    session_id: str = None,
    error_trace: str = None
) -> bool:
    """Save a system log entry."""
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO system_logs (log_level, component, message, session_id, error_trace)
            VALUES (?, ?, ?, ?, ?)
        ''', (log_level, component, message, session_id, error_trace))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving system log: {e}")
        return False


# ============== Data Cleanup ==============

def cleanup_old_sessions(days: int = 30) -> int:
    """Delete sessions older than specified days that are completed."""
    try:
        conn = get_db_connection()
        
        # Get sessions to delete
        sessions_to_delete = conn.execute('''
            SELECT session_id FROM sessions 
            WHERE created_at < datetime('now', ? || ' days')
            AND completed = TRUE
        ''', (-days,)).fetchall()
        
        count = len(sessions_to_delete)
        
        if count > 0:
            # Delete related data (cascade manually for SQLite)
            session_ids = [row['session_id'] for row in sessions_to_delete]
            placeholders = ','.join('?' * len(session_ids))
            
            # Delete from all related tables
            conn.execute(f'DELETE FROM chat_history WHERE session_id IN ({placeholders})', session_ids)
            conn.execute(f'DELETE FROM user_responses WHERE session_id IN ({placeholders})', session_ids)
            conn.execute(f'DELETE FROM risk_detections WHERE session_id IN ({placeholders})', session_ids)
            conn.execute(f'DELETE FROM session_summaries WHERE session_id IN ({placeholders})', session_ids)
            conn.execute(f'DELETE FROM intent_classifications WHERE session_id IN ({placeholders})', session_ids)
            conn.execute(f'DELETE FROM sessions WHERE session_id IN ({placeholders})', session_ids)
            
            conn.commit()
        
        conn.close()
        logger.info(f"Cleaned up {count} old sessions")
        return count
    except Exception as e:
        logger.error(f"Error cleaning up old sessions: {e}")
        return 0


# ============== Migration Helper ==============

def migrate_to_v2_schema():
    """Migrate existing database to v2 schema."""
    try:
        conn = get_db_connection()
        
        # Check if sessions table exists
        table_check = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sessions'
        """).fetchone()
        
        if not table_check:
            logger.info("Migrating to v2 schema...")
            
            # Read and execute v2 schema
            schema_path = os.path.join(script_dir, 'schema_v2.sql')
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
            
            # Migrate existing chat_history sessions to sessions table
            conn.execute('''
                INSERT OR IGNORE INTO sessions (session_id, created_at)
                SELECT DISTINCT session_id, MIN(ts) 
                FROM chat_history 
                GROUP BY session_id
            ''')
            
            conn.commit()
            logger.info("Migration to v2 schema completed")
        else:
            logger.info("v2 schema already exists")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise


if __name__ == "__main__":
    # Initialize database with v2 schema
    init_db()
    # Optionally migrate existing data
    migrate_to_v2_schema()