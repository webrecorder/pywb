from pywb.webapp.pywb_init import create_wb_router
from pywb.framework.wsgi_wrappers import init_app
from webtest import TestApp, TestResponse

app = None
testapp = None

def make_app(config_file, pywb_router=create_wb_router):
    app = init_app(pywb_router,
                   load_yaml=True,
                   config_file=config_file)

    testapp = TestApp(app)

    class Resp(TestResponse):
        def __init__(self, *args, **kwargs):
            super(Resp, self).__init__(*args, **kwargs)
            if self.headers.get('Content-Type'):
                self.charset = 'utf-8'

    TestApp.RequestClass.ResponseClass = Resp

    return app, testapp

def make_setup_module(config, pywb_router=create_wb_router):
    def setup_module():
        global app
        global testapp
        app, testapp = make_app(config, pywb_router)

    return setup_module

class BaseIntegration(object):
    def setup(self):
        self.app = app
        self.testapp = testapp
