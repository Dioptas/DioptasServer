import os
import threading

import numpy as np

from flask import Flask, request
from flask_socketio import SocketIO

from dioptas.model.DioptasModel import DioptasModel
import time

from .image_server import run_image_server

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sio = SocketIO(app, cors_allowed_origins="*")

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
    session = sessions[request.sid]
    session['server_thread'].close()
    del sessions[request.sid]


image_server_port = 61000


@sio.on('init_model')
def init_model():
    with get_session(request.sid) as session:
        print('init model')
        model = DioptasModel()
        session['model'] = model

        global image_server_port
        image_server_port += 1
        server_thread = threading.Thread(target=run_image_server,
                                         args=(image_server_port, model),
                                         daemon=True)
        server_thread.start()
        session['server_thread'] = server_thread
        session['server_port'] = image_server_port
        return image_server_port


def dummy_function():
    print('LDSGJASDLGAJSDGLHJASJLDHGASJLDDHGLJASJLDHJASDLHJALSJHLSAJDHLSAjhlsajhah')


def img_changed(sid):
    print('image changed')
    session = sessions[sid]
    model = session['model']  # type: DioptasModel
    sio.emit('img_changed', {
        'filename': os.path.relpath(model.img_model.filename, os.getcwd()).replace('\\', '/'),
        'serverPort': session['server_port']
    }, broadcast=True)


def pattern_changed(sid):
    session = sessions[sid]
    model = session['model']  # type: DioptasModel
    sio.emit('pattern_changed',
             {'filename': model.pattern_model.pattern_filename,
              'x': model.pattern_model.pattern.x.tolist(),
              'y': model.pattern_model.pattern.y.tolist()})


@sio.on('load_dummy')
def load_dummy():
    with get_session(request.sid) as session:
        model = session['model']  # type: DioptasModel
        model.load(os.path.join(data_path, 'projects', 'dummy.dio'))
        img_changed(request.sid)
        pattern_changed(request.sid)


@sio.on('load_dummy2')
def load_dummy2():
    with get_session(request.sid) as session:
        model = session['model']  # type: DioptasModel
        model.load(os.path.join(data_path, 'projects', 'dummy2.dio'))
        img_changed(request.sid)
        pattern_changed(request.sid)


@sio.on('load_image')
def load_image(filename):
    with get_session(request.sid) as session:
        model = session['model']  # type: DioptasModel
        model.img_model.load(filename)
        img_changed(request.sid)
        pattern_changed(request.sid)


@sio.on('load_next_image')
def load_next_image():
    with get_session(request.sid) as session:
        model = session['model']  # type: DioptasModel
        model.img_model.load_next_file()
        img_changed(request.sid)
        pattern_changed(request.sid)


@sio.on('load_previous_image')
def load_next_image():
    with get_session(request.sid) as session:
        model = session['model']  # type: DioptasModel
        model.img_model.load_previous_file()
        img_changed(request.sid)
        pattern_changed(request.sid)


@sio.on('list_dir')
def list_dir(base_directory):
    try:
        item_list = os.listdir(base_directory)
        folders = []
        files = []
        for item in item_list:
            if os.path.isdir(os.path.join(base_directory, item)):
                folders.append(item)
            else:
                files.append(item)
        return {'folders': folders, 'files': files}
    except FileNotFoundError:
        return None


@sio.on('get_image_angles')
def get_image_angles(x, y):
    session = sessions[request.sid]
    model = session['model']  # type: DioptasModel
    x, y = np.array([y]), np.array([x])  # have to be swapped for pyFAI
    tth_rad = model.calibration_model.get_two_theta_img(x, y)
    tth = np.rad2deg(tth_rad)
    azi = np.rad2deg(model.calibration_model.get_azi_img(x, y))
    q = 4 * np.pi * np.sin(tth / 360 * np.pi) / model.calibration_model.wavelength / 1e10
    d = model.calibration_model.wavelength / (2 * np.sin(tth / 360 * np.pi)) * 1e10
    return {'tth': tth, 'azi': azi, 'q': q, 'd': d}


@sio.on('get_pattern_angles')
def get_pattern_angles(tth):
    session = sessions[request.sid]
    model = session['model']  # type: DioptasModel
    q = 4 * np.pi * np.sin(tth / 360 * np.pi) / model.calibration_model.wavelength / 1e10
    d = model.calibration_model.wavelength / (2 * np.sin(tth / 360 * np.pi)) * 1e10
    return {'tth': tth, 'q': q, 'd': d}


def run_server(port):
    print("starting socket io server")
    sio.run(app, port=port)
    print("socket io server finished")


def start_server(port):
    sio.run(app, port=port)
