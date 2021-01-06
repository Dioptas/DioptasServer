from flask import Flask, request
from flask_socketio import SocketIO
from dioptas.model.DioptasModel import DioptasModel
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sio = SocketIO(app, cors_allowed_origins="*")

####################
# Session Handling:
# we currently lock the session when one event is e.g. reading from disk
# subsequent requests have to wait until the previous request is done.
# maybe a wait list is also necessary here, to be able to have each request
# answer in the same order as they came in...
##################

sessions = {}
locked_sessions = []


def get_session(sid, lock=True):
    if sid not in sessions:
        sessions[sid] = {}

    class _session_context_manager(object):
        def __init__(self, user_id, lock_session):
            self.sid = user_id
            self.session = sessions[user_id]
            self.lock = lock_session

        def __enter__(self):
            while self.sid in locked_sessions:
                time.sleep(0.001)
            if self.lock:
                locked_sessions.append(sid)
            return self.session

        def __exit__(self, _, value, traceback):
            if self.lock:
                del locked_sessions[locked_sessions.index(sid)]

    return _session_context_manager(sid, lock)


@sio.on('connect')
def connect():
    sessions[request.sid] = {}


@sio.on('disconnect')
def disconnect():
    del sessions[request.sid]


@sio.on('init_model')
def init_model():
    with get_session(request.sid) as session:
        session['model'] = DioptasModel()


def start_server(port):
    sio.run(app, port=port)
