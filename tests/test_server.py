import unittest

from dioptasserver.server import app, sio, sessions
from dioptas.model.DioptasModel import DioptasModel


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.client = sio.test_client(app)

    def test_init_model(self):
        self.client.emit('init_model')
        model = sessions[list(sessions.keys())[0]]['model']
        self.assertIsInstance(model, DioptasModel)
