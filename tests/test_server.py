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

    def test_load_image(self):
        self.client.emit('init_model')
        self.client.emit('load_image', '../data/images/image_001.tif')
        model = sessions[list(sessions.keys())[0]]['model']
        self.assertIn('image_001.tif', model.img_model.filename)

    def test_load_next_and_previous_image(self):
        self.client.emit('init_model')
        model = sessions[list(sessions.keys())[0]]['model']
        self.client.emit('load_image', '../data/images/image_001.tif')
        self.assertIn('image_001.tif', model.img_model.filename)
        self.client.emit('load_next_image')
        self.assertIn('image_002.tif', model.img_model.filename)
        self.client.emit('load_previous_image')
        self.assertIn('image_001.tif', model.img_model.filename)

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

        result = self.client.emit('list_dir', 'blub', callback=True)

    def test_get_image_angles(self):
        self.client.emit('init_model')
        result = self.client.emit('get_image_angles', 45, 100, callback=True)
        self.assertNotEqual(result, [])
        self.assertAlmostEqual(result['tth'], 0.4963, places=3)
        self.assertAlmostEqual(result['azi'], 65.7722, places=3)
        self.assertAlmostEqual(result['d'], 38.6019, places=3)
        self.assertAlmostEqual(result['q'], 0.162768, places=3)

    def test_get_pattern_angles(self):
        self.client.emit('init_model')
        result = self.client.emit('get_pattern_angles', 0.4963, callback=True)
        self.assertNotEqual(result, [])
        self.assertAlmostEqual(result['d'], 38.6052, places=3)
        self.assertAlmostEqual(result['q'], 0.162768, places=3)