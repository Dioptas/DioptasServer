import time
import threading
import unittest

from dioptasserver import start_tornado_server

import socketio


class TestSioServer(unittest.TestCase):
    port = 65231

    @classmethod
    def setUpClass(cls) -> None:
        cls.server_thread = threading.Thread(target=start_tornado_server,
                                             args=(cls.port,),
                                             daemon=True)
        cls.server_thread.start()

    def setUp(self):
        self.client = socketio.Client()
        self.client.connect("http://localhost:" + str(self.port))
        while '/' not in self.client.namespaces.keys():
            time.sleep(0.01)

    def tearDown(self) -> None:
        self.client.disconnect()

    def _callback(self, res=None):
        self.callback_result = res
        self.callback_called = True

    def emit(self, message: str, *args) -> object:
        self.callback_called = False
        self.callback_result = None

        self.client.emit(message, args, callback=self._callback)
        while not self.callback_called:
            time.sleep(0.01)
        return self.callback_result
