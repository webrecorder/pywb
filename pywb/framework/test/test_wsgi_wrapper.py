from pywb.framework.wsgi_wrappers import init_app

from pywb.utils.wbexception import AccessException

import webtest

class TestOkApp:
    def __call__(self, env):
        def response(env, start_response):
            start_response('200 OK', [])
            return [b'Test']
        return response

class TestErrApp:
    def __call__(self, env):
        raise Exception('Test Unexpected Error')

class TestCustomErrApp:
    def __call__(self, env):
        raise AccessException('Forbidden Test')


def initer(app_class):
    def init(config=None):
        return app_class()
    return init

def test_ok_app():
    the_app = init_app(initer(TestOkApp), load_yaml=False)

    testapp = webtest.TestApp(the_app)
    resp = testapp.get('/')

    assert resp.status_int == 200
    assert b'Test' in resp.body, resp.body

def test_err_app():
    the_app = init_app(initer(TestErrApp), load_yaml=False)

    testapp = webtest.TestApp(the_app)
    resp = testapp.get('/abc', expect_errors=True)

    assert resp.status_int == 500
    assert b'500 Internal Server Error Error: Test Unexpected Error' in resp.body

def test_custom_err_app():
    the_app = init_app(initer(TestCustomErrApp), load_yaml=False)

    testapp = webtest.TestApp(the_app)
    resp = testapp.get('/abc', expect_errors=True)

    assert resp.status_int == 403
    assert b'403 Access Denied Error: Forbidden Test' in resp.body




