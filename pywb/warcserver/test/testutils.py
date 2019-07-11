import json
import os
import tempfile
import shutil
import yaml
import time

from fakeredis import FakeStrictRedis, DATABASES
from mock import patch

from pywb.warcserver.basewarcserver import BaseWarcServer
from pywb.warcserver.handlers import DefaultResourceHandler

from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.index.indexsource import LiveIndexSource, MementoIndexSource

from pywb.utils.geventserver import GeventServer

from pywb import get_test_dir
from pywb.utils.wbexception import NotFoundException


# ============================================================================
def to_json_list(cdxlist, fields=['timestamp', 'load_url', 'filename', 'source']):
    return list([json.loads(cdx.to_json(fields)) for cdx in cdxlist])

def key_ts_res(cdxlist, extra='filename'):
    return '\n'.join([cdx['urlkey'] + ' ' + cdx['timestamp'] + ' ' + cdx[extra] for cdx in cdxlist])

def to_path(path):
    if os.path.sep != '/':
        path = path.replace('/', os.path.sep)

    return path


# ============================================================================
TEST_CDX_PATH = to_path(get_test_dir() + '/cdxj/')
TEST_WARC_PATH = to_path(get_test_dir() + '/warcs/')


# ============================================================================
class BaseTestClass(object):
    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        pass


# ============================================================================
PUBSUBS = []

class FakeStrictRedisSharedPubSub(FakeStrictRedis):
    def __init__(self, *args, **kwargs):
        super(FakeStrictRedisSharedPubSub, self).__init__(*args, **kwargs)
        self._pubsubs = PUBSUBS


# ============================================================================
class FakeRedisTests(object):
    @classmethod
    def setup_class(cls, redis_url='redis://localhost:6379/2'):
        super(FakeRedisTests, cls).setup_class()

        del PUBSUBS[:]
        DATABASES.clear()

        cls.redismock = patch('redis.StrictRedis', FakeStrictRedisSharedPubSub)
        cls.redismock.start()

        cls.redis = FakeStrictRedis.from_url(redis_url)

    @classmethod
    def add_cdx_to_redis(cls, filename, key):
        with open(filename, 'rb') as fh:
            for line in fh:
                cls.redis.zadd(key, 0, line.rstrip())

    @classmethod
    def teardown_class(cls):
        super(FakeRedisTests, cls).teardown_class()
        cls.redis.flushall()
        cls.redismock.stop()


# ============================================================================
class TempDirTests(object):
    @classmethod
    def setup_class(cls, *args, **kwargs):
        super(TempDirTests, cls).setup_class(*args, **kwargs)
        cls.root_dir = tempfile.mkdtemp()

    @classmethod
    def teardown_class(cls):
        super(TempDirTests, cls).teardown_class()
        shutil.rmtree(cls.root_dir)


# ============================================================================
class MementoOverrideTests(object):
    link_header_data = None
    orig_get_timegate_links = None

    @classmethod
    def setup_class(cls):
        super(MementoOverrideTests, cls).setup_class()

        # Load expected link headers
        MementoOverrideTests.link_header_data = None
        with open(to_path(get_test_dir() + '/text_content/link_headers.yaml')) as fh:
            MementoOverrideTests.link_header_data = yaml.load(fh)

        MementoOverrideTests.orig_get_timegate_links = MementoIndexSource.get_timegate_links

    @classmethod
    def mock_link_header(cls, test_name, load=False):
        def mock_func(self, params, closest):
            if load:
                res = cls.orig_get_timegate_links(self, params, closest)
                print(test_name + ': ')
                print("    '{0}': '{1}'".format(self.timegate_url, res))
                return res

            try:
                res = cls.link_header_data[test_name][self.timegate_url]
                time.sleep(0.2)
            except Exception as e:
                print(e)
                msg = self.timegate_url.format(url=params['url'])
                raise NotFoundException(msg)

            return res

        return mock_func


# ============================================================================
class LiveServerTests(object):
    @classmethod
    def setup_class(cls):
        super(LiveServerTests, cls).setup_class()
        cls.server = GeventServer(cls.make_live_app())

    @staticmethod
    def make_live_app():
        app = BaseWarcServer()
        app.add_route('/live',
            DefaultResourceHandler(SimpleAggregator(
                                   {'live': LiveIndexSource()})
            )
        )
        return app

    @classmethod
    def teardown_class(cls):
        cls.server.stop()
        super(LiveServerTests, cls).teardown_class()


# ============================================================================
class HttpBinLiveTests(object):
    @classmethod
    def setup_class(cls, *args, **kwargs):
        super(HttpBinLiveTests, cls).setup_class(*args, **kwargs)

        from httpbin import app as httpbin_app
        httpbin_app.config.update(JSONIFY_PRETTYPRINT_REGULAR=True)
        cls.httpbin_server = GeventServer(httpbin_app)

        httpbin_local = 'http://localhost:' + str(cls.httpbin_server.port) + '/'
        cls.httpbin_local = httpbin_local

        def get_load_url(self, params):
            params['url'] = params['url'].replace('http://test.httpbin.org/', httpbin_local)
            params['url'] = params['url'].replace('http://httpbin.org/', httpbin_local)
            params['url'] = params['url'].replace('https://httpbin.org/', httpbin_local)
            return params['url']

        cls.indexmock = patch('pywb.warcserver.index.indexsource.LiveIndexSource.get_load_url', get_load_url)
        cls.indexmock.start()

    @classmethod
    def get_httpbin_url(cls, url):
        return url.replace(cls.httpbin_local, 'http://httpbin.org/')

    @classmethod
    def teardown_class(cls):
        cls.indexmock.stop()
        cls.httpbin_server.stop()
        super(HttpBinLiveTests, cls).teardown_class()



