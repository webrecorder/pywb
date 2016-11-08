from gevent.monkey import patch_all; patch_all()

from bottle import run, Bottle, request, response, debug

from six.moves.urllib.parse import quote

from pywb.utils.loaders import LocalFileLoader

import mimetypes
import redis

from pywb.urlrewrite.rewriterapp import RewriterApp
from pywb.urlrewrite.cookies import CookieTracker


# ============================================================================
class RWApp(RewriterApp):
    def __init__(self, upstream_urls, cookie_key_templ, redis):
        config = {}
        config['url_templates'] = upstream_urls

        self.cookie_key_templ = cookie_key_templ
        self.app = Bottle()
        self.block_loader = LocalFileLoader()
        self.init_routes()

        super(RWApp, self).__init__(True, config=config)

        self.cookie_tracker = CookieTracker(redis)

        self.orig_error_handler = self.app.default_error_handler
        self.app.default_error_handler = self.err_handler

    def err_handler(self, exc):
        print(exc)
        import traceback
        traceback.print_exc()
        return self.orig_error_handler(exc)

    def get_cookie_key(self, kwargs):
        return self.cookie_key_templ.format(**kwargs)

    def init_routes(self):
        @self.app.get('/static/__pywb/<filepath:path>')
        def server_static(filepath):
            data = self.block_loader.load('pywb/static/' + filepath)
            guessed = mimetypes.guess_type(filepath)
            if guessed[0]:
                response.headers['Content-Type'] = guessed[0]

            return data

        self.app.mount('/live/', self.call_with_params(type='live'))
        self.app.mount('/record/', self.call_with_params(type='record'))
        self.app.mount('/replay/', self.call_with_params(type='replay'))

    @staticmethod
    def create_app(replay_port=8080, record_port=8010):
        upstream_urls = {'live': 'http://localhost:%s/live/resource/postreq?' % replay_port,
                         'record': 'http://localhost:%s/live/resource/postreq?' % record_port,
                         'replay': 'http://localhost:%s/replay/resource/postreq?' % replay_port,
                        }

        r = redis.StrictRedis.from_url('redis://localhost/2')
        rwapp = RWApp(upstream_urls, 'cookies:', r)
        return rwapp


# ============================================================================
if __name__ == "__main__":
    application = RWApp.create_app()
    application.app.run(port=8090, server='gevent')


