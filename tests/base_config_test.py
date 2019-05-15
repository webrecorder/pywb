from gevent import monkey; monkey.patch_all(thread=False)

import pytest
import webtest

from pywb.warcserver.test.testutils import BaseTestClass, TempDirTests
from pywb.manager.manager import main, CollectionsManager

from pywb.apps.frontendapp import FrontEndApp
import os


@pytest.fixture(params=['mp_', ''], ids=['frame', 'non-frame'])
def fmod(request):
    return request.param


@pytest.fixture(params=['mp_', ''], ids=['frame', 'non-frame'])
def fmod_sl(request):
    return request.param + '/' if request.param else ''


# ============================================================================
class BaseConfigTest(BaseTestClass):
    lint_app = True
    extra_headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.108 Safari/537.36'
    }

    @classmethod
    def get_test_app(cls, config_file, custom_config=None):
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
        app = FrontEndApp(config_file=config_file, custom_config=custom_config)
        return app, webtest.TestApp(app, lint=cls.lint_app)

    @classmethod
    def setup_class(cls, config_file, include_non_frame=True, custom_config=None):
        super(BaseConfigTest, cls).setup_class()
        cls.app, cls.testapp = cls.get_test_app(config_file, custom_config)

        if include_non_frame:
            custom_config = custom_config or {}
            custom_config['framed_replay'] = False
            cls.app_non_frame, cls.testapp_non_frame = cls.get_test_app(config_file,
                                                        custom_config)

    @classmethod
    def teardown_class(cls):
        if cls.app.recorder:
            cls.app.recorder.writer.close()

        if cls.app_non_frame.recorder:
            cls.app_non_frame.recorder.writer.close()

        super(BaseConfigTest, cls).teardown_class()

    def _assert_basic_html(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert resp.content_length > 0

    def _assert_basic_text(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/plain'
        assert resp.content_length > 0

    def get(self, url, fmod, *args, **kwargs):
        self.__ensure_headers(kwargs)
        app = self.testapp if fmod else self.testapp_non_frame
        return app.get(url.format(fmod), *args, **kwargs)

    def post(self, url, fmod, *args, **kwargs):
        self.__ensure_headers(kwargs)
        app = self.testapp if fmod else self.testapp_non_frame
        return app.post(url.format(fmod), *args, **kwargs)

    def post_json(self, url, fmod, *args, **kwargs):
        self.__ensure_headers(kwargs)
        app = self.testapp if fmod else self.testapp_non_frame
        return app.post_json(url.format(fmod), *args, **kwargs)

    def head(self, url, fmod, *args, **kwargs):
        self.__ensure_headers(kwargs)
        app = self.testapp if fmod else self.testapp_non_frame
        return app.head(url.format(fmod), *args, **kwargs)

    def __ensure_headers(self, kwargs):
        if 'headers' in kwargs:
            headers = kwargs.get('headers')
        else:
            headers = kwargs['headers'] = {}

        if isinstance(headers, dict) and 'User-Agent' not in headers:
            headers['User-Agent'] = self.extra_headers['User-Agent']


#=============================================================================
class CollsDirMixin(TempDirTests):
    COLLS_DIR = '_test_colls'

    @classmethod
    def setup_class(cls, *args, **kwargs):
        super(CollsDirMixin, cls).setup_class(*args, **kwargs)
        cls.orig_cwd = os.getcwd()
        cls.root_dir = os.path.realpath(cls.root_dir)
        os.chdir(cls.root_dir)
        cls.orig_collections = CollectionsManager.COLLS_DIR
        CollectionsManager.COLLS_DIR = cls.COLLS_DIR

    @classmethod
    def teardown_class(cls):
        os.chdir(cls.orig_cwd)
        CollectionsManager.COLLS_DIR = cls.orig_collections
        super(CollsDirMixin, cls).teardown_class()
