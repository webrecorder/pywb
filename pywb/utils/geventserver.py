import logging
import traceback

from gevent import spawn
from gevent.pywsgi import WSGIHandler, WSGIServer


# ============================================================================
class GeventServer(object):
    def __init__(self, app, port=0, hostname='localhost', handler_class=None,
                direct=False):
        self.port = port
        self.make_server(app, port, hostname, handler_class, direct=direct)

    def stop(self):
        if self.server:
            logging.debug('stopping server on ' + str(self.port))
            self.server.stop()

    def _run(self, server, port):
        logging.debug('starting server on ' + str(port))
        try:
            server.serve_forever()
        except Exception as e:
            logging.debug('server failed to start on ' + str(port))
            traceback.print_exc()

    def make_server(self, app, port, hostname, handler_class, direct=False):
        server = WSGIServer((hostname, port), app, handler_class=handler_class)
        server.init_socket()
        self.port = server.address[1]

        self.server = server
        if direct:
            self.ge = None
            self._run(server, self.port)
        else:
            self.ge = spawn(self._run, server, self.port)

    def join(self):
        self.ge.join()


# ============================================================================
class RequestURIWSGIHandler(WSGIHandler):
    def get_environ(self):
        environ = super(RequestURIWSGIHandler, self).get_environ()
        environ['REQUEST_URI'] = self.path
        return environ
