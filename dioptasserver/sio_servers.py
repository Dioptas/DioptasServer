import socketio

from .sio_events import connect_events
from .sessions import session_manager as sm


def make_tornado_app(sio):
    from tornado.web import Application
    import secrets
    return Application([
        (r"/socket.io/", socketio.get_tornado_handler(sio)),
    ], cookie_secret=secrets.token_bytes(16))


def start_tornado_server(port):
    import asyncio
    import tornado.ioloop
    sio = socketio.AsyncServer(async_mode='tornado', cors_allowed_origins="*")
    connect_events(sio, sm)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = make_tornado_app(sio)
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()


def start_eventlet_server(port):
    import eventlet
    sio = socketio.Server(async_mode='eventlet', cors_allowed_origins="*")
    connect_events(sio, sm)
    app = socketio.WSGIApp(sio)
    eventlet.wsgi.server(eventlet.listen(('', port)), app)


def start_gevent_server(port):
    sio = socketio.Server(async_mode='gevent', cors_allowed_origins="*")
    connect_events(sio, sm)
    app = socketio.WSGIApp(sio)
    from gevent import pywsgi
    pywsgi.WSGIServer(('', port), app).serve_forever()


def start_aio_server(port):
    sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins="*")
    connect_events(sio, sm)

    from aiohttp import web
    app = web.Application()
    sio.attach(app)
    web.run_app(app, port=port)


def start_sanic_server(port):
    sio = socketio.AsyncServer(async_mode='sanic', cors_allowed_origins='*')
    connect_events(sio, sm)

    from sanic import Sanic
    app = Sanic("Dioptas Server")
    sio.attach(app)
    app.run(port=port)



