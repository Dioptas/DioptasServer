import os
from tornado import testing, websocket
import numpy as np

from dioptasserver import make_app

from dioptas.model.DioptasModel import DioptasModel
from dioptasserver.sessions import session_manager

path = os.path.dirname(__file__)
data_path = os.path.join(path, '..', 'data')
image_path = os.path.join(data_path, 'images')


class TestImageHandler(testing.AsyncHTTPTestCase):
    def setUp(self) -> None:
        super(TestImageHandler, self).setUp()
        self.ws_url = "ws://localhost:" + str(self.get_http_port()) + "/image"
        session_manager.reset_sessions()

    def get_app(self):
        return make_app()

    @testing.gen_test
    def test_handshake(self):
        ws_client = yield websocket.websocket_connect(self.ws_url)
        response = yield ws_client.read_message()
        self.assertEqual('1', response)

    @testing.gen_test
    def test_load_non_existing_session(self):
        ws_client = yield websocket.websocket_connect(self.ws_url)
        _ = yield ws_client.read_message()  # discard handshake

        sid = '123'
        self.assertFalse(session_manager.has_sid(sid))

        ws_client.write_message(sid)
        response = yield ws_client.read_message()
        self.assertEqual(response, '0')

    @testing.gen_test
    def test_load_existing_session_no_model(self):
        ws_client = yield websocket.websocket_connect(self.ws_url)
        _ = yield ws_client.read_message()  # discard handshake

        sid = '123'
        self.assertFalse(session_manager.has_sid(sid))
        session_manager.get_session(sid)
        self.assertTrue(session_manager.has_sid(sid))

        ws_client.write_message(sid)
        response = yield ws_client.read_message()
        self.assertEqual(response, '0')

    @testing.gen_test
    def test_load_existing_session_with_model(self):
        ws_client = yield websocket.websocket_connect(self.ws_url)
        _ = yield ws_client.read_message()  # discard handshake

        sid = '123'
        with session_manager.get_session(sid) as session:
            session['model'] = DioptasModel()

        ws_client.write_message(sid)
        response = yield ws_client.read_message()
        self.assertEqual(response, '1')

    @testing.gen_test
    def test_new_image_is_send(self):
        ws_client = yield websocket.websocket_connect(self.ws_url)
        _ = yield ws_client.read_message()  # discard handshake

        sid = '123'
        with session_manager.get_session(sid) as session:
            session['model'] = DioptasModel()

        ws_client.write_message(sid)
        response = yield ws_client.read_message()
        self.assertEqual(response, '1')

        with session_manager.get_session(sid) as session:
            model = session['model']  # type: DioptasModel
            model.img_model.load(os.path.join(image_path, 'image_001.tif'))

        response = yield ws_client.read_message()
        self.assertGreater(len(response), 10)
