import os
import threading

import numpy as np
from dioptas.model import OverlayModel
from skimage.measure import find_contours

from flask import Flask, request
from flask_socketio import SocketIO

from dioptas.model.DioptasModel import DioptasModel
import time

from .image_server import run_image_server

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sio = SocketIO(app, cors_allowed_origins="*", async_handlers=True)

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

from functools import partial


@sio.on('init_model')
def init_model():
    with get_session(request.sid) as session:
        print('init model')
        model = DioptasModel()
        model.img_changed.connect(partial(img_changed, request.sid), priority=True)
        model.pattern_changed.connect(partial(pattern_changed, request.sid), priority=True)
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


def img_changed(sid):
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


@sio.on('load_dummy2')
def load_dummy2():
    with get_session(request.sid) as session:
        model = session['model']  # type: DioptasModel
        model.load(os.path.join(data_path, 'projects', 'dummy2.dio'))


@sio.on('load_image')
def load_image(filename):
    with get_session(request.sid) as session:
        model = session['model']  # type: DioptasModel
        model.img_model.load(filename)


@sio.on('load_next_image')
def load_next_image():
    with get_session(request.sid) as session:
        model = session['model']  # type: DioptasModel
        model.img_model.load_next_file()


@sio.on('load_previous_image')
def load_next_image():
    with get_session(request.sid) as session:
        model = session['model']  # type: DioptasModel
        model.img_model.load_previous_file()


@sio.on('list_dir')
def list_dir(base_directory):
    print('listing directory: ', base_directory)
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
    if model.calibration_model.is_calibrated:
        tth_rad = model.calibration_model.get_two_theta_img(x, y)
        tth = np.rad2deg(tth_rad)
        azi = np.rad2deg(model.calibration_model.get_azi_img(x, y))
        q = 4 * np.pi * np.sin(tth / 360 * np.pi) / model.calibration_model.wavelength / 1e10
        d = model.calibration_model.wavelength / (2 * np.sin(tth / 360 * np.pi)) * 1e10
        return {'tth': tth, 'azi': azi, 'q': q, 'd': d}
    else:
        return {'tth': None, 'azi': None, 'q': None, 'd': None}


@sio.on('get_pattern_angles')
def get_pattern_angles(tth):
    session = sessions[request.sid]
    model = session['model']  # type: DioptasModel
    if model.calibration_model.is_calibrated:
        q = 4 * np.pi * np.sin(tth / 360 * np.pi) / model.calibration_model.wavelength / 1e10
        d = model.calibration_model.wavelength / (2 * np.sin(tth / 360 * np.pi)) * 1e10
        return {'tth': tth, 'q': q, 'd': d}
    else:
        return {'tth': None, 'q': None, 'd': None}


@sio.on('get_azimuthal_ring')
def get_azimuthal_ring(tth):
    """
    Calculates 1-4 segments of an azimuthal ring with a Two Theta value of tth
    :param tth: Two-Theta in degrees
    :return: a dictionary with a a list of x- and y- values for each segment (up to 4)
    {'x': [seg1, seg2, ... ], 'y': [seg1, seg2,...]}
    """
    session = sessions[request.sid]
    model = session['model']  # type: DioptasModel
    if not model.calibration_model.is_calibrated:
        return {'x': None, 'y': None}
    tth = np.deg2rad(tth)
    tth_array = model.calibration_model.get_two_theta_array()
    tth_ind = find_contours(tth_array, tth)
    x = [[]] * 4
    y = [[]] * 4
    for i in range(len(tth_ind)):
        x[i] = ((tth_ind[i][:, 1] + 0.5).tolist())
        y[i] = ((tth_ind[i][:, 0] + 0.5).tolist())
    return {'x': x, 'y': y}


###################################
# Overlay Stuff:
##################################

def connect_overlay_signals(overlay_model: OverlayModel):
    overlay_model.overlay_added.connect(overlay_added)
    overlay_model.overlay_changed.connect(overlay_changed)
    overlay_model.overlay_removed.connect(overlay_removed)


def overlay_added():
    sio.emit('overlay_added')


def overlay_removed(index):
    sio.emit('overlay_removed', index)


def overlay_changed(index):
    sio.emit('overlay_changed', index)


@sio.on('pattern_as_overlay')
def pattern_as_overlay():
    session = sessions[request.sid]
    model = session['model']  # type: DioptasModel
    model.overlay_model.add_overlay_pattern(model.pattern_model.pattern)


@sio.on('get_overlay')
def get_overlay(index):
    session = sessions[request.sid]
    model = session['model']  # type: DioptasModel
    overlay = model.overlay_model.overlays[index]
    return {
        'name': overlay.name,
        'x': overlay.x,
        'y': overlay.y,
        'offset': overlay.offset,
        'scaling': overlay.scaling
    }


@sio.on('get_overlays')
def get_overlays():
    session = sessions[request.sid]
    model = session['model']  # type: DioptasModel
    result = []
    for overlay in model.overlay_model.overlays:
        result.append({
            'name': overlay.name,
            'x': overlay.x,
            'y': overlay.y,
            'offset': overlay.offset,
            'scaling': overlay.scaling})
    return result


def run_server(port):
    print("starting socket io server")
    sio.run(app, port=port)
    print("socket io server finished")


def start_server(port):
    sio.run(app, port=port)
