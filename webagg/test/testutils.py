import json
import os
import tempfile
import shutil

from multiprocessing import Process

from fakeredis import FakeStrictRedis
from mock import patch

from wsgiref.simple_server import make_server

from webagg.aggregator import SimpleAggregator
from webagg.app import ResAggApp
from webagg.handlers import DefaultResourceHandler
from webagg.indexsource import LiveIndexSource


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
    def setup_class(cls):
        super(FakeRedisTests, cls).setup_class()
        cls.redismock = patch('redis.StrictRedis', FakeStrictRedisSharedPubSub)
        cls.redismock.start()

    @staticmethod
    def add_cdx_to_redis(filename, key, redis_url='redis://localhost:6379/2'):
        r = FakeStrictRedis.from_url(redis_url)
        with open(filename, 'rb') as fh:
            for line in fh:
                r.zadd(key, 0, line.rstrip())

    @classmethod
    def teardown_class(cls):
        super(FakeRedisTests, cls).teardown_class()
        cls.redismock.stop()


# ============================================================================
class TempDirTests(object):
    @classmethod
    def setup_class(cls):
        super(TempDirTests, cls).setup_class()
        cls.root_dir = tempfile.mkdtemp()

    @classmethod
    def teardown_class(cls):
        super(TempDirTests, cls).teardown_class()
        shutil.rmtree(cls.root_dir)


# ============================================================================
class LiveServerTests(object):
    @classmethod
    def setup_class(cls):
        super(LiveServerTests, cls).setup_class()
        cls.server = ServerThreadRunner(cls.make_live_app())

    @staticmethod
    def make_live_app():
        app = ResAggApp()
        app.add_route('/live',
            DefaultResourceHandler(SimpleAggregator(
                                   {'live': LiveIndexSource()})
            )
        )
        return app

    @classmethod
    def teardown_class(cls):
        super(LiveServerTests, cls).teardown_class()
        cls.server.stop()


# ============================================================================
class ServerThreadRunner(object):
    def __init__(self, app):
        self.httpd = make_server('', 0, app)
        self.port = self.httpd.socket.getsockname()[1]

        def run():
            self.httpd.serve_forever()

        self.proc = Process(target=run)
        #self.proc.daemon = True
        self.proc.start()

    def stop(self):
        self.proc.terminate()


