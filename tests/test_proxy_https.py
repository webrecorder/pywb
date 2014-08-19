from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app

from wsgiref.simple_server import make_server

import threading
import requests
import shutil
import os

TEST_CONFIG = 'tests/test_config_proxy.yaml'
CA_BUNDLE = 'pywb-ca.pem'

TEST_CA_DIR = './tests/pywb_test_certs'
TEST_CA_ROOT = './tests/pywb_test_ca.pem'

server = None
proxy_str = None

def setup_module():
    global server
    server = ServeThread()
    server.daemon = True
    server.start()
 

def teardown_module():
    try:
        server.httpd.shutdown()
        threading.current_thread().join(server)
    except Exception:
        pass

    # delete test root and certs
    shutil.rmtree(TEST_CA_DIR)
    os.remove(TEST_CA_ROOT)


class ServeThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(ServeThread, self).__init__(*args, **kwargs)
        self.app = init_app(create_wb_router,
                            load_yaml=True,
                            config_file=TEST_CONFIG)
 
        # init with port 0 to allow os to pick a port
        self.httpd = make_server('', 0, self.app)
        port = self.httpd.socket.getsockname()[1]

        proxy_str = 'http://localhost:' + str(port)
        self.proxy_dict = {'http': proxy_str, 'https': proxy_str}

    def run(self, *args, **kwargs):
        self.httpd.serve_forever()


def test_replay():
    resp = requests.get('https://iana.org/',
                        proxies=server.proxy_dict,
                        verify=False)
#                        verify=CA_BUNDLE)
    assert resp.status_code == 200


def test_replay_static():
    resp = requests.get('https://pywb.proxy/static/default/wb.js',
                        proxies=server.proxy_dict,
                        headers={'Connection': 'close'},
                        verify=False)
#                        verify=CA_BUNDLE)
    assert resp.status_code == 200
    found = u'function init_banner' in resp.text
    assert found, resp.text
    resp.close()
