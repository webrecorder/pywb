import threading

from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app

# disable is_hop_by_hop restrictions
import wsgiref.handlers
wsgiref.handlers.is_hop_by_hop = lambda x: False


class ServerThreadRunner(object):
    def __init__(self, make_httpd, config_file=None):

        if config_file:
            self.app = init_app(create_wb_router,
                                load_yaml=True,
                                config_file=config_file)
        else:
            self.app = None

        self.httpd = make_httpd(self.app)
        self.port = self.httpd.socket.getsockname()[1]

        proxy_str = 'http://localhost:' + str(self.port)
        self.proxy_str = proxy_str
        self.proxy_dict = {'http': proxy_str,
                           'https': proxy_str}

        def run():
            self.httpd.serve_forever()

        self.thread = threading.Thread(target=run)
        self.thread.daemon = True
        self.thread.start()

    def stop_thread(self):
        self.httpd.shutdown()
