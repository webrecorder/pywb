from gevent.wsgi import WSGIServer
from gevent import spawn
import logging


# ============================================================================
class GeventServer(object):
    def __init__(self, app, port=0, hostname='localhost', handler_class=None):
        self.port = port
        self.make_server(app, port, hostname, handler_class)

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

    def make_server(self, app, port, hostname, handler_class):
        server = WSGIServer((hostname, port), app, handler_class=handler_class)
        server.init_socket()
        self.port = server.address[1]

        self.server = server
        self.ge = spawn(self._run, server, self.port)

    def join(self):
        self.ge.join()


