from .base_config_test import BaseConfigTest, fmod_sl

import os
import pytest


# ============================================================================
class TestSOCKSProxy(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        pytest.importorskip('socks')
        os.environ['SOCKS_HOST'] = 'localhost'
        os.environ['SOCKS_PORT'] = '0'

        super(TestSOCKSProxy, cls).setup_class('config_test.yaml')

    @classmethod
    def teardown_class(cls):
        super(TestSOCKSProxy, cls).teardown_class()

    @pytest.mark.skipif(os.environ.get('CI') is not None, reason='Skip Test on CI')
    def test_socks_attempt_connect(self, fmod_sl):
        # no proxy is set, expect to fail if socks is being used
        resp = self.get('/live/{0}http://httpbin.org/get', fmod_sl, status=400)
        assert resp.status_int == 400

    @pytest.mark.skipif(os.environ.get('CI') is not None, reason='Skip Test on CI')
    def test_socks_disable_enable(self, fmod_sl):
        os.environ['SOCKS_DISABLE'] = '1'

        resp = self.get('/live/{0}http://httpbin.org/get', fmod_sl, status=200)
        assert resp.status_int == 200

        os.environ['SOCKS_DISABLE'] = ''

        resp = self.get('/live/{0}http://httpbin.org/get', fmod_sl, status=400)
        assert resp.status_int == 400
