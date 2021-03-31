import os

from dioptas.model.DioptasModel import DioptasModel

from .utils import TestSioServer
from dioptasserver import sm


path = os.path.dirname(__file__)
data_path = os.path.join(path, '..', 'data')
image_path = os.path.join(data_path, 'images')


class TestSIO(TestSioServer):
    def test_init_model(self):
        self.emit('init_model')
        model = sm.sessions[list(sm.sessions.keys())[0]]['model']
        self.assertIsInstance(model, DioptasModel)

    def test_load_dummy(self):
        self.emit('init_model')
        self.emit('load_dummy')
        model = sm.sessions[list(sm.sessions.keys())[0]]['model']
        self.assertEqual(model.img_model.filename, 'D:/Programming/Dioptas/dioptas/tests/data/CeO2_Pilatus1M.tif')
        self.assertEqual(model.img_model.img_data.shape, (1043, 981))

    def test_load_image(self):
        self.emit('init_model')
        self.emit('load_image', os.path.join(image_path, 'image_001.tif'))
        model = sm.sessions[list(sm.sessions.keys())[0]]['model']
        self.assertIn('image_001.tif', model.img_model.filename)

    def test_load_next_and_previous_image(self):
        self.emit('init_model')
        model = sm.sessions[list(sm.sessions.keys())[0]]['model']
        self.emit('load_image', os.path.join(image_path, 'image_001.tif'))
        self.assertIn('image_001.tif', model.img_model.filename)
        self.emit('load_next_image')
        self.assertIn('image_002.tif', model.img_model.filename)
        self.emit('load_previous_image')
        self.assertIn('image_001.tif', model.img_model.filename)

    def test_listdir(self):
        result = self.emit('list_dir', data_path)
        self.assertIn('images', result['folders'])
        self.assertIn('projects', result['folders'])

        result = self.emit('list_dir', os.path.join(data_path, 'projects'))
        self.assertIn('dummy.dio', result['files'])
        self.assertIn('dummy2.dio', result['files'])

        result = self.emit('list_dir', image_path)
        self.assertIn('image_001.tif', result['files'])
        self.assertIn('image_002.tif', result['files'])

    def test_get_image_angles(self):
        self.emit('init_model')

        result = self.emit('get_image_angles', 45, 100)
        self.assertNotEqual(result, [])
        self.assertIsNone(result['tth'])

        self.emit('load_dummy')
        result = self.emit('get_image_angles', 45, 100)
        self.assertAlmostEqual(result['tth'], 26.679, places=2)
        self.assertAlmostEqual(result['azi'], -136.9883, places=3)
        self.assertAlmostEqual(result['d'], 0.88114, places=3)
        self.assertAlmostEqual(result['q'], 7.13072, places=3)

    def test_get_pattern_angles(self):
        self.emit('init_model')
        result = self.emit('get_pattern_angles', 0.4963)
        self.assertNotEqual(result, [])
        self.assertIsNone(result['d'])
        self.assertIsNone(result['q'])

        self.emit('load_dummy')
        result = self.emit('get_pattern_angles', 0.4963)

        self.assertAlmostEqual(result['d'], 46.9404, places=3)
        self.assertAlmostEqual(result['q'], 0.13385, places=3)

    def test_get_azimuthal_ring(self):
        self.emit('init_model')
        self.emit('load_dummy')
        result = self.emit('get_azimuthal_ring', 5)
        self.assertNotEqual(result, [])
        self.assertGreater(len(result['x']), 0)
        self.assertGreater(len(result['y']), 0)
