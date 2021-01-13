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


def run_image_server(port, dioptas_model: DioptasModel):
    # Create tornado application and supply URL routes

    class ChannelHandler(tornado.websocket.WebSocketHandler, metaclass=ABCMeta):
        """
        Handler that handles a websocket channel
        """

        def on_message(self, message: object) -> object:
            """
            Message received on channel
            """
            print('receives message: ', message)
            print('send image')
            self.write_message(convert_array_to_bytes(dioptas_model.img_model.img_data), binary=True)

        def check_origin(self, origin):
            """
            Override the origin check if needed
            """
            return True

    asyncio.set_event_loop(asyncio.new_event_loop())
    app = tornado.web.Application([(r'/', ChannelHandler), ])
    app.listen(port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    run_image_server(PORT)
