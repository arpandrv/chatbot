from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from core.router import route_message
from core.session import new_session_id, get_session
import os

from database.repository import init_db

load_dotenv()

init_db()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id')
    if not session_id:
        session_id = new_session_id()
    
    session = get_session(session_id)
    fsm = session['fsm']
    reply = route_message(session_id, message)
    
    return jsonify({
        'reply': reply,
        'session_id': session_id,
        'state': fsm.state,
        'flags': {}
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True)
