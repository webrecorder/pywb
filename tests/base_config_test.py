from gevent import monkey; monkey.patch_all(thread=False)

from webtest import TestApp

from pywb.webagg.test.testutils import BaseTestClass

from pywb.urlrewrite.frontendapp import FrontEndApp
import os


# ============================================================================
class BaseConfigTest(BaseTestClass):
    @classmethod
    def setup_class(cls, config_file):
        super(BaseConfigTest, cls).setup_class()
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
        cls.testapp = TestApp(FrontEndApp(config_file=config_file))


