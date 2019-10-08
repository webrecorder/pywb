import logging
import traceback

from gevent import spawn
from gevent.pywsgi import WSGIHandler, WSGIServer


# ============================================================================
class GeventServer(object):
    """Class for optionally running a WSGI application in a greenlet"""

    def __init__(self, app, port=0, hostname='localhost', handler_class=None,
                 direct=False):
        """Initialize a new GeventServer instance

        :param app: The WSGI application instance to be used
        :param int port: The port the server is to listen on
        :param str hostname: The hostname the server is to use
        :param handler_class: The class to be used for handling WSGI requests
        :param bool direct: T/F indicating if the server should be run in a greenlet
        or in current thread
        """
        self.port = port
        self.server = None
        self.ge = None
        self.make_server(app, port, hostname, handler_class, direct=direct)

    def stop(self):
        """Stops the running server if it was started"""
        if self.server:
            logging.debug('stopping server on ' + str(self.port))
            self.server.stop()

    def _run(self, server, port):
        """Start running the server forever

        :param server: The server to be run
        :param int port: The port the server is to listen on
        """
        logging.debug('starting server on ' + str(port))
        try:
            server.serve_forever()
        except Exception as e:
            logging.debug('server failed to start on ' + str(port))
            traceback.print_exc()

    def make_server(self, app, port, hostname, handler_class, direct=False):
        """Creates and starts the server. If direct is true the server is run
        in the current thread otherwise in a greenlet.

        :param app: The WSGI application instance to be used
        :param int port: The port the server is to listen on
        :param str hostname: The hostname the server is to use
        :param handler_class: The class to be used for handling WSGI requests
        :param bool direct: T/F indicating if the server should be run in a greenlet
        or in current thread
        """
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
        """Joins the greenlet spawned for running the server if it was started
        in non-direct mode"""
        if self.ge:
            self.ge.join()


# ============================================================================
class RequestURIWSGIHandler(WSGIHandler):
    """A specific WSGIHandler subclass that adds `REQUEST_URI` to the environ dictionary
    for every request
    """

    def get_environ(self):
        """Returns the WSGI environ dictionary with the
        `REQUEST_URI` added to it

        :return: The WSGI environ dictionary for the request
        :rtype: dict
        """
        environ = super(RequestURIWSGIHandler, self).get_environ()
        environ['REQUEST_URI'] = self.path
        return environ
