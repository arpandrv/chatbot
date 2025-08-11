import uuid
from core.fsm import ChatBotFSM

sessions = {}

def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {'fsm': ChatBotFSM(session_id)}
    return sessions[session_id]

def new_session_id():
    return str(uuid.uuid4())
