from pywb.warcserver.test.testutils import BaseTestClass, TempDirTests

from .base_config_test import CollsDirMixin
from pywb.utils.geventserver import GeventServer
from pywb.apps.frontendapp import FrontEndApp
from pywb.apps.cli import wayback
from pywb.manager.manager import main as manager

from mock import patch

import os
import requests
import pytest


# ============================================================================
@pytest.fixture(params=['http', 'https'])
def scheme(request):
    return request.param


# ============================================================================
class BaseTestProxy(TempDirTests, BaseTestClass):
    @classmethod
    def setup_class(cls, coll='pywb', config_file='config_test.yaml', recording=False):
        super(BaseTestProxy, cls).setup_class()
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)

        cls.root_ca_file = os.path.join(cls.root_dir, 'pywb-ca-test.pem')

        opts = {'ca_name': 'pywb test HTTPS Proxy CA',
                'ca_file_cache': cls.root_ca_file,
                'coll': coll,
                'recording': recording,
               }

        cls.app = FrontEndApp(config_file=config_file,
                              custom_config={'proxy': opts})

        cls.server = GeventServer(cls.app)
        cls.proxies = cls.proxy_dict(cls.server.port)

    @classmethod
    def teardown_class(cls):
        cls.server.stop()

        super(BaseTestProxy, cls).teardown_class()

    @classmethod
    def proxy_dict(cls, port, host='localhost'):
        return {'http': 'http://{0}:{1}'.format(host, port),
                'https': 'https://{0}:{1}'.format(host, port)
               }


# ============================================================================
class TestProxy(BaseTestProxy):
    def test_proxy_replay(self, scheme):
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        assert 'WB Insert' in res.text
        assert 'Example Domain' in res.text

        assert res.headers['Link'] == '<http://example.com>; rel="memento"; datetime="Mon, 27 Jan 2014 17:12:51 GMT"'
        assert res.headers['Memento-Datetime'] == 'Mon, 27 Jan 2014 17:12:51 GMT'


# ============================================================================
class TestRecordingProxy(CollsDirMixin, BaseTestProxy):
    @classmethod
    def setup_class(cls, coll='pywb', config_file='config_test.yaml'):
        super(TestRecordingProxy, cls).setup_class('test', 'config_test_record.yaml', recording=True)
        manager(['init', 'test'])

    @classmethod
    def teardown_class(cls):
        if cls.app.recorder:
            cls.app.recorder.writer.close()
        super(TestRecordingProxy, cls).teardown_class()

    def test_proxy_record(self, scheme):
        archive_dir = os.path.join(self.root_dir, '_test_colls', 'test', 'archive')
        assert os.path.isdir(archive_dir)

        res = requests.get('{0}://httpbin.org/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        assert 'is_live = true' in res.text
        assert 'httpbin(1)' in res.text

        assert len(os.listdir(archive_dir)) == 1

    def test_proxy_replay_recorded(self, scheme):
        manager(['reindex', 'test'])

        self.app.handler.prefix_resolver.fixed_prefix = '/test/bn_/'

        res = requests.get('{0}://httpbin.org/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        assert 'is_live = false' in res.text
        assert 'httpbin(1)' in res.text


# ============================================================================
def _run_patch(self):
    return self


@patch('pywb.apps.cli.ReplayCli.run', _run_patch)
class TestProxyCLIConfig(object):
    def test_proxy_cli(self):
        res = wayback(['--proxy', 'test'])
        exp = {'ca_file_cache': os.path.join('proxy-certs', 'pywb-ca.pem'),
               'ca_name': 'pywb HTTPS Proxy CA',
               'coll': 'test',
               'recording': False}
        assert res.extra_config['proxy'] == exp

    def test_proxy_cli_rec(self):
        res = wayback(['--proxy', 'test', '--proxy-record'])
        assert res.extra_config['proxy']['recording'] == True
        assert res.extra_config['collections']['live'] == {'index': '$live', 'use_js_obj_proxy': True}

    def test_proxy_cli_err_coll(self):
        with pytest.raises(Exception):
            res = wayback(['--proxy', 'test/foo'])


