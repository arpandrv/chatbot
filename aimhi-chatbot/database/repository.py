import sqlite3
import os

# Use absolute path for database file in database/ folder
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
default_db_path = os.path.join(script_dir, 'chat_history.db')  # Put in database/ folder

# Handle both SQLite file paths and SQLAlchemy URLs
database_url = os.getenv('DATABASE_URL', default_db_path)
if database_url.startswith('sqlite:///'):
    # Convert SQLAlchemy URL to file path
    DATABASE_URL = database_url.replace('sqlite:///', '')
    if not os.path.isabs(DATABASE_URL):
        DATABASE_URL = os.path.join(project_root, DATABASE_URL)
else:
    DATABASE_URL = database_url

def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        # Ensure the database directory exists
        db_dir = os.path.dirname(DATABASE_URL)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        conn = get_db_connection()
        script_dir = os.path.dirname(__file__)
        schema_path = os.path.join(script_dir, 'schema.sql')
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        conn.close()
        print(f"Database initialized at: {DATABASE_URL}")
    except Exception as e:
        print(f"Database initialization error: {e}")
        print(f"Attempted database path: {DATABASE_URL}")
        # Try creating a minimal database inline
        try:
            conn = sqlite3.connect(DATABASE_URL)
            conn.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT CHECK(role IN ('user','bot')) NOT NULL,
                message TEXT NOT NULL,
                ts DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_session_ts ON chat_history(session_id, ts)')
            conn.close()
            print("Database created inline successfully")
        except Exception as e2:
            print(f"Inline database creation also failed: {e2}")
            raise

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
