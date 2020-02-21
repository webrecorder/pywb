from pywb.warcserver.test.testutils import BaseTestClass, TempDirTests, HttpBinLiveTests

from .base_config_test import CollsDirMixin
from pywb.utils.geventserver import GeventServer, RequestURIWSGIHandler
from pywb.apps.frontendapp import FrontEndApp
from pywb.manager.manager import main as manager

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
    def setup_class(cls, coll='pywb', config_file='config_test.yaml', recording=False,
                    proxy_opts={}, config_opts={}):

        super(BaseTestProxy, cls).setup_class()
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)

        cls.root_ca_file = os.path.join(cls.root_dir, 'pywb-ca-test.pem')

        opts = {'ca_name': 'pywb test HTTPS Proxy CA',
                'ca_file_cache': cls.root_ca_file,
                'coll': coll,
                'recording': recording,
               }

        opts.update(proxy_opts)

        custom_config = config_opts
        custom_config['proxy'] = opts

        cls.app = FrontEndApp(config_file=config_file,
                              custom_config=custom_config)

        cls.server = GeventServer(cls.app, handler_class=RequestURIWSGIHandler)
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

        assert 'Example Domain' in res.text

        # wb insert
        assert 'WB Insert' in res.text

        # no wombat.js and wombatProxyMode.js
        assert 'wombat.js' not in res.text
        assert 'wombatProxyMode.js' not in res.text

        # no redirect check
        assert 'window == window.top' not in res.text

        # no auto fetch
        assert 'wbinfo.enable_auto_fetch = false;' in res.text

        assert res.headers['Link'] == '<http://example.com>; rel="memento"; datetime="Mon, 27 Jan 2014 17:12:51 GMT"; collection="pywb"'
        assert res.headers['Memento-Datetime'] == 'Mon, 27 Jan 2014 17:12:51 GMT'
        assert 'Content-Location' not in res.headers

    def test_proxy_replay_cors(self, scheme):
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file,
                           headers={'Origin': '{0}://api.example.com/'.format(scheme)})

        assert 'Example Domain' in res.text

        assert res.headers['Access-Control-Allow-Methods'] == 'GET, POST, PUT, OPTIONS, DELETE, PATCH, HEAD, TRACE, CONNECT'
        assert res.headers['Access-Control-Allow-Credentials'] == 'true'
        assert res.headers['Access-Control-Allow-Origin'] == '{0}://api.example.com/'.format(scheme)

        assert 'Content-Location' not in res.headers

    def test_proxy_replay_change_dt(self, scheme):
        headers = {'Accept-Datetime':  'Mon, 26 Dec 2011 17:12:51 GMT'}
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           headers=headers,
                           verify=self.root_ca_file)

        assert 'WB Insert' in res.text
        assert 'Example Domain' in res.text

        # no wombat.js and wombatProxyMode.js
        assert 'wombat.js' not in res.text
        assert 'wombatProxyMode.js' not in res.text

        # no auto fetch
        assert 'wbinfo.enable_auto_fetch = false;' in res.text

        # banner
        assert 'default_banner.js' in res.text

        # no redirect check
        assert 'window == window.top' not in res.text

        assert res.headers['Link'] == '<http://test@example.com/>; rel="memento"; datetime="Mon, 29 Jul 2013 19:51:51 GMT"; collection="pywb"'
        assert res.headers['Memento-Datetime'] == 'Mon, 29 Jul 2013 19:51:51 GMT'


# ============================================================================
class TestProxyDefaultDate(BaseTestProxy):
    @classmethod
    def setup_class(cls):
        super(TestProxyDefaultDate, cls).setup_class(proxy_opts={'default_timestamp': '20111226181251'})

    def test_proxy_default_replay_dt(self, scheme):
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        assert 'WB Insert' in res.text
        assert 'Example Domain' in res.text

        # no wombat.js and wombatProxyMode.js
        assert 'wombat.js' not in res.text
        assert 'wombatProxyMode.js' not in res.text

        # no auto fetch
        assert 'wbinfo.enable_auto_fetch = false;' in res.text

        # banner
        assert 'default_banner.js' in res.text

        # no redirect check
        assert 'window == window.top' not in res.text

        assert res.headers['Link'] == '<http://test@example.com/>; rel="memento"; datetime="Mon, 29 Jul 2013 19:51:51 GMT"; collection="pywb"'
        assert res.headers['Memento-Datetime'] == 'Mon, 29 Jul 2013 19:51:51 GMT'
        assert 'Content-Location' not in res.headers


# ============================================================================
class TestRedirectClassicProxy(TestProxy):
    @classmethod
    def setup_class(cls):
        super(TestRedirectClassicProxy, cls).setup_class('pywb', config_file='config_test_redirect_classic.yaml')

    def test_proxy_replay_prefer_raw(self, scheme):
        headers = {'Prefer': 'raw'}
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           headers=headers,
                           verify=self.root_ca_file)

        # no rewriting
        assert 'WB Insert' not in res.text
        assert 'wbinfo' not in res.text

        # content
        assert 'Example Domain' in res.text

        # no wombat.js
        assert 'wombat.js' not in res.text

        # no redirect check
        assert 'window == window.top' not in res.text

        assert res.headers['Link'] == '<http://example.com>; rel="memento"; datetime="Mon, 27 Jan 2014 17:12:51 GMT"; collection="pywb"'
        assert res.headers['Memento-Datetime'] == 'Mon, 27 Jan 2014 17:12:51 GMT'
        assert res.headers['Preference-Applied'] == 'raw'
        assert 'Content-Location' not in res.headers

    def test_proxy_replay_prefer_rewritten_to_banner_only(self, scheme):
        headers = {'Prefer': 'rewritten'}
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           headers=headers,
                           verify=self.root_ca_file)

        assert 'WB Insert' in res.text
        assert 'Example Domain' in res.text

        # no wombat.js
        assert 'wombat.js' not in res.text

        # no redirect check
        assert 'window == window.top' not in res.text

        assert res.headers['Link'] == '<http://example.com>; rel="memento"; datetime="Mon, 27 Jan 2014 17:12:51 GMT"; collection="pywb"'
        assert res.headers['Memento-Datetime'] == 'Mon, 27 Jan 2014 17:12:51 GMT'
        assert res.headers['Preference-Applied'] == 'banner-only'
        assert 'Content-Location' not in res.headers

    def test_proxy_replay_prefer_banner_only(self, scheme):
        headers = {'Prefer': 'banner-only'}
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           headers=headers,
                           verify=self.root_ca_file)

        assert 'WB Insert' in res.text
        assert 'Example Domain' in res.text

        # no wombat.js
        assert 'wombat.js' not in res.text

        # no redirect check
        assert 'window == window.top' not in res.text

        assert res.headers['Link'] == '<http://example.com>; rel="memento"; datetime="Mon, 27 Jan 2014 17:12:51 GMT"; collection="pywb"'
        assert res.headers['Memento-Datetime'] == 'Mon, 27 Jan 2014 17:12:51 GMT'
        assert res.headers['Preference-Applied'] == 'banner-only'

    def test_proxy_replay_prefer_invalid(self, scheme):
        headers = {'Prefer': 'invalid'}
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           headers=headers,
                           verify=self.root_ca_file)

        assert 'Preference-Applied' not in res.headers
        assert res.status_code == 400


# ============================================================================
class TestRecordingProxy(HttpBinLiveTests, CollsDirMixin, BaseTestProxy):
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

        self.app.proxy_prefix = '/test/bn_/'

        res = requests.get('{0}://httpbin.org/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        assert 'is_live = false' in res.text
        assert 'httpbin(1)' in res.text

    def test_proxy_record_keep_percent(self, scheme):
        self.app.proxy_prefix = '/test/record/bn_/'

        res = requests.get('{0}://example.com/path/%2A%2Ftest'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        # ensure %-encoded url stays as is
        assert '"{0}://example.com/path/%2A%2Ftest"'.format(scheme) in res.text


# ============================================================================
class TestProxyNoBanner(BaseTestProxy):
    @classmethod
    def setup_class(cls):
        super(TestProxyNoBanner, cls).setup_class(proxy_opts={'enable_banner': False})

    def test_proxy_replay(self, scheme):
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        # content
        assert 'Example Domain' in res.text

        # head insert
        assert 'WB Insert' in res.text

        # no banner
        assert 'default_banner.js' not in res.text

        # no wombat.js and wombatProxyMode.js
        assert 'wombat.js' not in res.text
        assert 'wombatProxyMode.js' not in res.text

        # no auto fetch
        assert 'wbinfo.enable_auto_fetch = false;' in res.text

        # no redirect check
        assert 'window == window.top' not in res.text

        assert res.headers['Link'] == '<http://example.com>; rel="memento"; datetime="Mon, 27 Jan 2014 17:12:51 GMT"; collection="pywb"'
        assert res.headers['Memento-Datetime'] == 'Mon, 27 Jan 2014 17:12:51 GMT'


# ============================================================================
class TestProxyNoHeadInsert(BaseTestProxy):
    @classmethod
    def setup_class(cls):
        super(TestProxyNoHeadInsert, cls).setup_class(proxy_opts={'enable_content_rewrite': False})

    def test_proxy_replay(self, scheme):
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        # content
        assert 'Example Domain' in res.text

        # no head insert
        assert 'WB Insert' not in res.text

        # no banner
        assert 'default_banner.js' not in res.text

        # no wombat.js and wombatProxyMode.js
        assert 'wombat.js' not in res.text
        assert 'wombatProxyMode.js' not in res.text

        # no redirect check
        assert 'window == window.top' not in res.text

        assert res.headers['Link'] == '<http://example.com>; rel="memento"; datetime="Mon, 27 Jan 2014 17:12:51 GMT"; collection="pywb"'
        assert res.headers['Memento-Datetime'] == 'Mon, 27 Jan 2014 17:12:51 GMT'


# ============================================================================
class TestProxyIncludeBothWombatAutoFetchWorker(BaseTestProxy):
    @classmethod
    def setup_class(cls):
        super(TestProxyIncludeBothWombatAutoFetchWorker, cls).setup_class(
            proxy_opts={'enable_wombat': True}, config_opts={'enable_auto_fetch': True}
        )

    def test_include_both_wombat_auto_fetch_worker(self, scheme):
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        # content
        assert 'Example Domain' in res.text

        # yes head insert
        assert 'WB Insert' in res.text

        # no wombat.js, yes wombatProxyMode.js
        assert 'wombat.js' not in res.text
        assert 'wombatProxyMode.js' in res.text
        assert 'wbinfo.enable_auto_fetch = true;' in res.text


# ============================================================================
class TestProxyIncludeWombatNotAutoFetchWorker(BaseTestProxy):
    @classmethod
    def setup_class(cls):
        super(TestProxyIncludeWombatNotAutoFetchWorker, cls).setup_class(
            proxy_opts={'enable_wombat': True}, config_opts={'enable_auto_fetch': False}
        )

    def test_include_wombat_not_auto_fetch_worker(self, scheme):
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        # content
        assert 'Example Domain' in res.text

        # yes head insert
        assert 'WB Insert' in res.text

        # no wombat.js, yes wombatProxyMode.js
        assert 'wombat.js' not in res.text
        assert 'wombatProxyMode.js' in res.text
        assert 'wbinfo.enable_auto_fetch = false;' in res.text


# ============================================================================
class TestProxyIncludeAutoFetchWorkerNotWombat(BaseTestProxy):
    @classmethod
    def setup_class(cls):
        super(TestProxyIncludeAutoFetchWorkerNotWombat, cls).setup_class(
            proxy_opts={'enable_wombat': False}, config_opts={'enable_auto_fetch': True}
        )

    def test_include_auto_fetch_worker_not_wombat(self, scheme):
        res = requests.get('{0}://example.com/'.format(scheme),
                           proxies=self.proxies,
                           verify=self.root_ca_file)

        # content
        assert 'Example Domain' in res.text

        # yes head insert
        assert 'WB Insert' in res.text

        assert 'wombat.js' not in res.text

        # auto fetch worker requires wombatProxyMode.js
        assert 'wombatProxyMode.js' in res.text
        assert 'wbinfo.enable_auto_fetch = true;' in res.text


# ============================================================================
class TestProxyAutoFetchWorkerEndPoints(CollsDirMixin, BaseTestProxy):
    @classmethod
    def setup_class(cls):
        super(TestProxyAutoFetchWorkerEndPoints, cls).setup_class(
            coll='test2',
            config_file='config_test_record.yaml',
            proxy_opts={'enable_wombat': True}, config_opts={'enable_auto_fetch': True},
            recording=True
        )
        manager(['init', 'test2'])

    def test_proxy_fetch_options_request(self, scheme):
        expected_origin = '{0}://example.com'.format(scheme)
        res = requests.options('{0}://pywb.proxy/proxy-fetch/{1}'.format(scheme, expected_origin),
                               headers=dict(Origin=expected_origin),
                               proxies=self.proxies, verify=self.root_ca_file)

        assert res.ok
        assert res.headers.get('Access-Control-Allow-Origin') == expected_origin

    def test_proxy_fetch(self, scheme):
        expected_origin = '{0}://example.com'.format(scheme)
        res = requests.get('{0}://pywb.proxy/proxy-fetch/{1}'.format(scheme, expected_origin),
                           headers=dict(Origin='{0}://example.com'.format(scheme)),
                           proxies=self.proxies, verify=self.root_ca_file)
        assert res.ok
        assert 'Example Domain' in res.text

        res = requests.get('{0}://pywb.proxy/proxy-fetch/{1}'.format(scheme, expected_origin),
                           proxies=self.proxies, verify=self.root_ca_file)

        assert res.ok
        assert 'Example Domain' in res.text

    def test_proxy_worker_options_request(self, scheme):
        expected_origin = '{0}://example.com'.format(scheme)
        res = requests.options('{0}://pywb.proxy/static/autoFetchWorker.js'.format(scheme),
                               headers=dict(Origin=expected_origin),
                               proxies=self.proxies, verify=self.root_ca_file)

        assert res.ok
        assert res.headers.get('Access-Control-Allow-Origin') == expected_origin

    def test_proxy_worker_fetch(self, scheme):
        origin = '{0}://example.com'.format(scheme)
        url = '{0}://pywb.proxy/static/autoFetchWorker.js'.format(scheme)
        res = requests.get(url,
                           headers=dict(Origin=origin),
                           proxies=self.proxies, verify=self.root_ca_file)

        assert res.ok
        assert res.headers.get('Content-Type') == 'application/javascript'
        assert res.headers.get('Access-Control-Allow-Origin') == origin
        assert 'function handleSrcsetProxyMode' in res.text

        res = requests.get(url, proxies=self.proxies, verify=self.root_ca_file)

        assert res.ok
        assert res.headers.get('Content-Type') == 'application/javascript'
        assert res.headers.get('Access-Control-Allow-Origin') == '*'
        assert 'function handleSrcsetProxyMode' in res.text
