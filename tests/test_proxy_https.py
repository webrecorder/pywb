from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app

from wsgiref.simple_server import make_server

from pywb.framework.proxy_resolvers import CookieResolver

import threading
import requests
import shutil
import os

TEST_CONFIG = 'tests/test_config_proxy.yaml'

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
    #cookie_val = CookieResolver.SESH_COOKIE_NAME + '=
    resp = requests.get('https://iana.org/',
                        proxies=server.proxy_dict,
    #                    headers={'Cookie': cookie_val},
                        verify=TEST_CA_ROOT)
    assert resp.status_code == 200


def test_replay_static():
    resp = requests.get('https://pywb.proxy/static/default/wb.js',
                        proxies=server.proxy_dict,
                        verify=TEST_CA_ROOT)
    assert resp.status_code == 200
    found = u'function init_banner' in resp.text
    assert found, resp.text

def test_replay_dl_page():
    resp = requests.get('https://pywb.proxy/',
                        proxies=server.proxy_dict,
                        verify=TEST_CA_ROOT)
    assert resp.status_code == 200
    assert 'text/html' in resp.headers['content-type']
    found = u'Download' in resp.text
    assert found, resp.text

def test_dl_pem():
    resp = requests.get('https://pywb.proxy/pywb-ca.pem',
                        proxies=server.proxy_dict,
                        verify=TEST_CA_ROOT)

    assert resp.headers['content-type'] == 'application/x-x509-ca-cert'

def test_dl_p12():
    resp = requests.get('https://pywb.proxy/pywb-ca.p12',
                        proxies=server.proxy_dict,
                        verify=TEST_CA_ROOT)

    assert resp.headers['content-type'] == 'application/x-pkcs12'

