from gevent import monkey; monkey.patch_all(thread=False)

import pytest
import webtest

from pywb.warcserver.test.testutils import BaseTestClass

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
    @classmethod
    def get_test_app(cls, config_file, override=None):
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
        return webtest.TestApp(FrontEndApp(config_file=config_file, custom_config=override))

    @classmethod
    def setup_class(cls, config_file, include_non_frame=True):
        super(BaseConfigTest, cls).setup_class()
        cls.testapp = cls.get_test_app(config_file)

        if include_non_frame:
            cls.testapp_non_frame = cls.get_test_app(config_file,
                                                     override={'framed_replay': False})
    def _assert_basic_html(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert resp.content_length > 0

    def _assert_basic_text(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/plain'
        assert resp.content_length > 0

    def get(self, url, fmod, *args, **kwargs):
        app = self.testapp if fmod else self.testapp_non_frame
        return app.get(url.format(fmod), *args, **kwargs)

    def post(self, url, fmod, *args, **kwargs):
        app = self.testapp if fmod else self.testapp_non_frame
        return app.post(url.format(fmod), *args, **kwargs)

    def post_json(self, url, fmod, *args, **kwargs):
        app = self.testapp if fmod else self.testapp_non_frame
        return app.post_json(url.format(fmod), *args, **kwargs)

    def head(self, url, fmod, *args, **kwargs):
        app = self.testapp if fmod else self.testapp_non_frame
        return app.head(url.format(fmod), *args, **kwargs)


