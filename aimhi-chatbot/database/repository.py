import sqlite3
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'chat_history.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    script_dir = os.path.dirname(__file__)
    schema_path = os.path.join(script_dir, 'schema.sql')
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    conn.close()

def save_message(session_id, role, message):
    conn = get_db_connection()
    conn.execute('INSERT INTO chat_history (session_id, role, message) VALUES (?, ?, ?)',
                 (session_id, role, message))
    conn.commit()
    conn.close()

def get_history(session_id, limit=6):
    conn = get_db_connection()
    history = conn.execute('SELECT role, message FROM chat_history WHERE session_id = ? ORDER BY ts DESC LIMIT ?',
                            (session_id, limit)).fetchall()
    conn.close()
    return history
