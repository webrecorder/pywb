from gevent.monkey import patch_all; patch_all()

from bottle import run, Bottle, request, response

from six.moves.urllib.parse import quote

from pywb.utils.loaders import LocalFileLoader
import mimetypes

from urlrewrite.rewriterapp import RewriterApp


# ============================================================================
class RWApp(RewriterApp):
    def __init__(self, upstream_urls):
        self.upstream_urls = upstream_urls
        self.app = Bottle()
        self.block_loader = LocalFileLoader()
        self.init_routes()
        super(RWApp, self).__init__(True)

    def get_upstream_url(self, url, wb_url, closest, kwargs):
        type = kwargs.get('type')
        return self.upstream_urls[type].format(url=quote(url),
                                               closest=closest)

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
        upstream_urls = {'live': 'http://localhost:%s/live/resource/postreq?url={url}&closest={closest}' % replay_port,
                         'record': 'http://localhost:%s/live/resource/postreq?url={url}&closest={closest}' % record_port,
                         'replay': 'http://localhost:%s/replay/resource/postreq?url={url}&closest={closest}' % replay_port,
                        }

        rwapp = RWApp(upstream_urls)
        return rwapp


# ============================================================================
if __name__ == "__main__":
    application = RWApp.create_app()
    application.app.run(port=8090, server='gevent')


