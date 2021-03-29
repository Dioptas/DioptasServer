from abc import ABCMeta
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.websocket
import tornado.options

from dioptas.model.DioptasModel import DioptasModel
from .util import convert_array_to_bytes

import asyncio
import os

if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PORT = 64333


class ImageHandler(tornado.websocket.WebSocketHandler, metaclass=ABCMeta):
    """
    Handler that handles a websocket channel
    """

    def initialize(self, dioptas_model: DioptasModel):
        self.dioptas_model = dioptas_model
        self.dioptas_model.pattern_changed.connect(self.send_image, priority=True)

    def __del__(self):
        self.dioptas_model.pattern_changed.disconnect(self.send_image)

    def send_image(self):
        byte_image = convert_array_to_bytes(self.dioptas_model.img_model.img_data)
        self.write_message(byte_image, binary=True)

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


def run_image_server(port, dioptas_model: DioptasModel):
    # Create tornado application and supply URL routes
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = tornado.web.Application([(r'/', ImageHandler, dict(dioptas_model=dioptas_model)), ])
    app.listen(port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    run_image_server(PORT)
