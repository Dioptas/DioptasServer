from dioptasserver import start_tornado_server, start_eventlet_server, start_gevent_server, start_aio_server, \
    start_sanic_server
import sys

if __name__ == "__main__":
    if len(sys.argv) == 1:
        port = 8745
    else:
        port = sys.argv[1]
    # start_eventlet_server(port)
    # start_gevent_server(port)
    # start_tornado_server(port)
    # start_aio_server(port)
    start_sanic_server(port)
