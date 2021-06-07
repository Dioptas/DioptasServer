from functools import partial
import os

from skimage.measure import find_contours

from dioptas.model import OverlayModel
from dioptas.model.DioptasModel import DioptasModel
import numpy as np

from .util import run_coroutine, convert_array_to_bytes

path = os.path.dirname(__file__)
data_path = os.path.join(path, '../data')


def connect_events(sio, session_manager):
    @sio.on('connect')
    def connect(sid, data):
        session_manager.sessions[sid] = {}
        print(sid, 'connected!')
        return sid

    @sio.on('disconnect')
    def disconnect(sid):
        print(sid, 'disconnected!')
        del session_manager.sessions[sid]

    @sio.on('init_model')
    def init_model(sid):
        with session_manager.get_session(sid) as session:
            print('init model')
            model = DioptasModel()
            model.img_changed.connect(partial(img_changed, sid), priority=True)
            model.pattern_changed.connect(partial(pattern_changed, sid))
            connect_overlay_signals(sid, model.overlay_model)
            session['model'] = model

    def img_changed(sid):
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        byte_image = convert_array_to_bytes(model.img_model.img_data)
        run_coroutine(
            sio.emit('img_changed', {
               # 'filename': os.path.relpath(model.img_model.filename, os.getcwd()).replace('\\', '/'),
                'filename': model.img_model.filename.replace('\\', '/'),
                'image': byte_image
            })
        )

    def pattern_changed(sid):
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        run_coroutine(
            sio.emit('pattern_changed',
                     {'filename': model.pattern_model.pattern_filename,
                      'x': model.pattern_model.pattern.x.tolist(),
                      'y': model.pattern_model.pattern.y.tolist()})
        )

    @sio.on('load_dummy')
    def load_dummy(sid):
        with session_manager.get_session(sid) as session:
            model = session['model']  # type: DioptasModel
            model.load(os.path.join(data_path, 'projects', 'dummy.dio'))

    @sio.on('load_dummy2')
    def load_dummy2(sid):
        with session_manager.get_session(sid) as session:
            global t1
            model = session['model']  # type: DioptasModel
            model.load(os.path.join(data_path, 'projects', 'dummy2.dio'))

    @sio.on('load_image')
    def load_image(sid, filename):
        with session_manager.get_session(sid) as session:
            model = session['model']  # type: DioptasModel
            model.img_model.load(filename)

    @sio.on('load_next_image')
    def load_next_image(sid):
        with session_manager.get_session(sid) as session:
            model = session['model']  # type: DioptasModel
            model.img_model.load_next_file()

    @sio.on('load_previous_image')
    def load_previous_image(sid):
        with session_manager.get_session(sid) as session:
            model = session['model']  # type: DioptasModel
            model.img_model.load_previous_file()

    @sio.on('list_dir')
    def list_dir(sid, base_directory):
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
    def get_image_angles(sid, x, y):
        session = session_manager.sessions[sid]
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
    def get_pattern_angles(sid, tth):
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        if model.calibration_model.is_calibrated:
            q = 4 * np.pi * np.sin(tth / 360 * np.pi) / model.calibration_model.wavelength / 1e10
            d = model.calibration_model.wavelength / (2 * np.sin(tth / 360 * np.pi)) * 1e10
            return {'tth': tth, 'q': q, 'd': d}
        else:
            return {'tth': None, 'q': None, 'd': None}

    @sio.on('get_azimuthal_ring')
    def get_azimuthal_ring(sid, tth):
        """
        Calculates 1-4 segments of an azimuthal ring with a Two Theta value of tth
        :param tth: Two-Theta in degrees
        :return: a dictionary with a a list of x- and y- values for each segment (up to 4)
        {'x': [seg1, seg2, ... ], 'y': [seg1, seg2,...]}
        """
        session = session_manager.sessions[sid]
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

    def connect_overlay_signals(sid, overlay_model: OverlayModel):
        overlay_model.overlay_added.connect(partial(overlay_added, sid))
        overlay_model.overlay_changed.connect(partial(overlay_changed, sid))
        overlay_model.overlay_removed.connect(overlay_removed)

    def overlay_added(sid):
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        overlay = model.overlay_model.overlays[-1]
        result = {
            'name': overlay.name,
            'x': overlay.x.tolist(),
            'y': overlay.y.tolist(),
            'offset': float(overlay.offset),
            'scaling': float(overlay.scaling)
        }
        run_coroutine(sio.emit('overlay_added', result))

    def overlay_changed(sid, index):
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        overlay = model.overlay_model.overlays[index]
        result = {
            'name': overlay.name,
            'x': overlay.x.tolist(),
            'y': overlay.y.tolist(),
            'offset': float(overlay.offset),
            'scaling': float(overlay.scaling)
        }
        run_coroutine(sio.emit('overlay_changed',
                               {
                                   'index': index,
                                   'overlay': result
                               }))

    def overlay_removed(index):
        run_coroutine(sio.emit('overlay_removed', index))

    @sio.on('pattern_as_overlay')
    def pattern_as_overlay(sid):
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        model.overlay_model.add_overlay_pattern(model.pattern_model.pattern)

    @sio.on('clear_overlays')
    def clear_overlays(sid):
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        model.overlay_model.reset()

    @sio.on('set_overlay_scaling')
    def set_overlay_scaling(sid, payload):
        print('set overlay scaling', payload)
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        model.overlay_model.set_overlay_scaling(int(payload['ind']), float(payload['scaling']))

    @sio.on('set_overlay_offset')
    def set_overlay_offset(sid, payload):
        print('set overlay offset', payload)
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        model.overlay_model.set_overlay_offset(int(payload['ind']), float(payload['offset']))

    @sio.on('get_overlay')
    def get_overlay(sid, index):
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        overlay = model.overlay_model.overlays[index]
        return {
            'name': overlay.name,
            'x': overlay.x.tolist(),
            'y': overlay.y.tolist(),
            'offset': float(overlay.offset),
            'scaling': float(overlay.scaling)
        }

    @sio.on('get_overlays')
    def get_overlays(sid):
        session = session_manager.sessions[sid]
        model = session['model']  # type: DioptasModel
        result = []
        for overlay in model.overlay_model.overlays:
            result.append({
                'name': overlay.name,
                'x': overlay.x.tolist(),
                'y': overlay.y.tolist(),
                'offset': float(overlay.offset),
                'scaling': float(overlay.scaling)})
        return result
