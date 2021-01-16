import unittest
import os

from dioptasserver.server import app, sio, sessions
from dioptas.model.DioptasModel import DioptasModel

path = os.path.dirname(__file__)
data_path = os.path.join(path, '../data')


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.client = sio.test_client(app)
        self.sid = list(sessions.keys())[0]

    def test_init_model(self):
        self.client.emit('init_model')
        model = sessions[list(sessions.keys())[0]]['model']
        self.assertIsInstance(model, DioptasModel)

    def test_load_dummy(self):
        self.client.emit('init_model')
        self.client.emit('load_dummy')
        model = sessions[list(sessions.keys())[0]]['model']
        self.assertEqual(model.img_model.filename, 'D:/Programming/Dioptas/dioptas/tests/data/CeO2_Pilatus1M.tif')
        self.assertEqual(model.img_model.img_data.shape, (1043, 981))
        received_events = [event['name'] for event in self.client.get_received()]
        self.assertIn('img_changed', received_events)
        self.assertIn('pattern_changed', received_events)

    def test_listdir(self):
        result = self.client.emit('list_dir', '../data', callback=True)
        self.assertIn('images', result['folders'])
        self.assertIn('projects', result['folders'])

        result = self.client.emit('list_dir', '../data/projects', callback=True)
        self.assertIn('dummy.dio', result['files'])
        self.assertIn('dummy2.dio', result['files'])

        result = self.client.emit('list_dir', '../data/images', callback=True)
        self.assertIn('image_001.tif', result['files'])
        self.assertIn('image_002.tif', result['files'])



