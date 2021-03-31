from abc import ABCMeta
import tornado.websocket
import tornado.options

from dioptas.model import DioptasModel

from .util import convert_array_to_bytes
from .sessions import session_manager as sm


class ImageHandler(tornado.websocket.WebSocketHandler, metaclass=ABCMeta):
    """
    Handler that handles a websocket channel
    """

    def __init__(self, *args, **kwargs):
        super(ImageHandler, self).__init__(*args, **kwargs)
        self.dioptas_model = None

    def open(self, *args):
        print('New connection to ImageHandler')
        self.write_message('1')

    def on_message(self, message):
        sid = message
        if sid in sm.sessions.keys():
            if 'model' in sm.sessions[sid].keys():
                self.dioptas_model = sm.sessions[sid]['model']  # type: DioptasModel
                self.dioptas_model.img_changed.connect(self.send_image, priority=True)
                self.write_message('1')
                # self.send_image()
            else:
                self.write_message('0')
        else:
            self.write_message('0')

    def send_image(self):
        byte_image = convert_array_to_bytes(self.dioptas_model.img_model.img_data)
        self.write_message(byte_image, binary=True)
        print('Image Changed, sending image with filename: ', self.dioptas_model.img_model.filename)

    def on_close(self):
        if self.dioptas_model:
            self.dioptas_model.img_changed.disconnect(self.send_image)

    def check_origin(self, origin):
        """
        Override the origin check if needed
        """
        return True

    def get_compression_options(self):
        return {
            'compression_level': 1,
            'mem_level': 7
        }
