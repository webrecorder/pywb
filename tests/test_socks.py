from .base_config_test import BaseConfigTest, fmod_sl

import pywb.warcserver.http as pywb_http
import os
import socket
import gevent
import pytest


# ============================================================================
class TestSOCKSProxy(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        os.environ['SOCKS_HOST'] = 'localhost'
        os.environ['SOCKS_PORT'] = '0'

        pywb_http.patch_socks()
        import pywb.warcserver.resource.responseloader
        pywb.warcserver.resource.responseloader.SOCKS_PROXIES = pywb_http.SOCKS_PROXIES
        super(TestSOCKSProxy, cls).setup_class('config_test.yaml')

    @classmethod
    def teardown_class(cls):
        pywb_http.unpatch_socks()
        super(TestSOCKSProxy, cls).teardown_class()

    def test_socks_proxy_set(self):
        assert pywb_http.SOCKS_PROXIES == {'http': 'socks5h://localhost:0',
                                           'https': 'socks5h://localhost:0'
                                          }

    def test_socks_attempt_connect(self, fmod_sl):
        pytest.importorskip('socks')
        # no proxy is set, expect to fail if socks is being used
        resp = self.get('/live/{0}http://httpbin.org/get', fmod_sl, status=400)
        assert resp.status_int == 400


