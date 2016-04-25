from gevent.monkey import patch_all; patch_all()

from bottle import run, Bottle, request, response

from six.moves.urllib.parse import quote

from pywb.utils.loaders import LocalFileLoader
import mimetypes

from urlrewrite.rewriterapp import RewriterApp


# ============================================================================
class RWApp(RewriterApp):
    def __init__(self, upstream_url):
        self.upstream_url = upstream_url
        self.app = Bottle()
        self.block_loader = LocalFileLoader()
        self.init_routes()
        super(RWApp, self).__init__(True)

    def get_upstream_url(self, url, wb_url, closest, kwargs):
        return self.upstream_url.format(url=quote(url),
                                        closest=closest,
                                        type=kwargs.get('type'))

    def init_routes(self):
        @self.app.get('/static/__pywb/<filepath:path>')
        def server_static(filepath):
            data = self.block_loader.load('pywb/static/' + filepath)
            guessed = mimetypes.guess_type(filepath)
            if guessed[0]:
                response.headers['Content-Type'] = guessed[0]

            return data

        self.app.mount('/live/', self.call_with_params(type='live'))
        self.app.mount('/replay/', self.call_with_params(type='replay-testdata'))


# ============================================================================
if __name__ == "__main__":
    rwapp = RWApp('http://localhost:8080/{type}/resource/postreq?url={url}&closest={closest}')
    rwapp.app.run(port=8090)


