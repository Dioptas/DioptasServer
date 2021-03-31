import asyncio
import socketio
import tornado.ioloop
from tornado.web import Application
import secrets

from .sessions import session_manager as sm
from .sio_server import sio
from .image_server import ImageHandler


def make_app():
    return Application([
        (r"/socket.io/", socketio.get_tornado_handler(sio)),
        (r"/image", ImageHandler),
    ], cookie_secret=secrets.token_bytes(16))


def start_server(port):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = make_app()
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    start_server(9456)
