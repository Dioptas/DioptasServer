import os
from functools import partial

from flask import Flask, request
from flask_socketio import SocketIO

from dioptas.model.DioptasModel import DioptasModel
import time

from .util import convert_array_to_bytes

from qtpy import QtCore


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sio = SocketIO(app, cors_allowed_origins="*", binary=True)

path = os.path.dirname(__file__)
data_path = os.path.join(path, '../data')

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
    print(request.sid, 'connected!')
    return request.sid


@sio.on('disconnect')
def disconnect():
    print(request.sid, 'disconnected!')
    del sessions[request.sid]


@sio.on('init_model')
def init_model():
    with get_session(request.sid) as session:
        print('init model')
        model = DioptasModel()
        # setting up signals:
        model.img_changed.connect(partial(img_changed, request.sid))
        model.pattern_changed.connect(partial(pattern_changed, request.sid))
        model.img_model.filename = 'Wurstbrot'
        session['model'] = model


def dummy_function():
    print('LDSGJASDLGAJSDGLHJASJLDHGASJLDDHGLJASJLDHJASDLHJALSJHLSAJDHLSAjhlsajhah')


def img_changed(sid):
    print('image changed')
    session = sessions[sid]
    model = session['model']  # type: DioptasModel
    sio.emit('img_changed', convert_array_to_bytes(model.img_model.img_data))
    # namespace='/' + sid)


def pattern_changed(sid):
    session = sessions[sid]
    model = session['model']  # type: DioptasModel
    sio.emit('pattern_changed',
             (model.pattern_model.pattern_filename,
              model.pattern_model.pattern.x,
              model.pattern_model.pattern.y),
             namespace='/' + sid)


@sio.on('load_dummy')
def load_dummy():
    with get_session(request.sid) as session:
        print('load dummy')
        model = session['model']
        model.img_changed.connect(partial(img_changed, request.sid))
        model.pattern_changed.connect(partial(pattern_changed, request.sid))
        print(model.img_model.filename)
        model.load(os.path.join(data_path, 'dummy.dio'))
        # img_changed(request.sid)
        model.img_changed.emit()


def run_server(port):
    print("starting socket io server")
    sio.run(app, port=port)
    print("socket io server finished")


class DioptasServer(object):
    def __init__(self):
        self.pyqt_app = QtCore.QCoreApplication([])
        self.pyqt_app.setQuitLockEnabled(True)
        self.sio = sio

    def start(self, port):
        self.sio.run(sio.run(app, port=port))


def start_server(port):
    dioptas_server = DioptasServer()
    dioptas_server.start(port)
