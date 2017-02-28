from gevent.monkey import patch_all; patch_all()

#from bottle import run, Bottle, request, response, debug
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import pop_path_info
from six.moves.urllib.parse import urljoin

from pywb.webagg.autoapp import AutoConfigApp
from pywb.webapp.handlers import StaticHandler

from pywb.framework.wbrequestresponse import WbResponse

from pywb.urlrewrite.geventserver import GeventServer
from pywb.urlrewrite.templateview import BaseInsertView

from pywb.urlrewrite.rewriterapp import RewriterApp, UpstreamException
import traceback


# ============================================================================
class NewWbRequest(object):
    def __init__(self, env, wb_url_str, full_prefix):
        self.env = env
        self.wb_url_str = wb_url_str
        self.full_prefix = full_prefix


# ============================================================================
class FrontEndApp(RewriterApp):
    def __init__(self, config_file='./config.yaml', custom_config=None):
        super(FrontEndApp, self).__init__(True)

        self.debug = True
        self.webagg = AutoConfigApp(config_file=config_file,
                                    custom_config=custom_config)

        self.webagg_server = GeventServer(self.webagg, port=0)

        self.static_handler = StaticHandler('pywb/static/')

        self.url_map = Map()
        self.url_map.add(Rule('/static/__pywb/<path:filepath>', endpoint=self.serve_static))
        self.url_map.add(Rule('/<coll>/', endpoint=self.serve_coll_page))
        self.url_map.add(Rule('/<coll>/<path:url>', endpoint=self.serve_content))
        self.url_map.add(Rule('/collinfo.json', endpoint=self.serve_listing))
        self.url_map.add(Rule('/', endpoint=self.serve_home))

        self.paths = self.get_upstream_paths(self.webagg_server.port)

    def get_upstream_paths(self, port):
        return {'replay-dyn': 'http://localhost:%s/_/resource/postreq?param.coll={coll}' % port,
                'replay-fixed': 'http://localhost:%s/{coll}/resource/postreq' % port
               }

    def serve_home(self, environ):
        home_view = BaseInsertView(self.jinja_env, 'new_index.html')
        routes = self.webagg.list_fixed_routes() + self.webagg.list_dynamic_routes()

        content = home_view.render_to_string(environ, routes=routes)
        return WbResponse.text_response(content, content_type='text/html; charset="utf-8"')

    def serve_static(self, environ, filepath=''):
        try:
            return self.static_handler(NewWbRequest(environ, filepath, ''))
        except:
            raise NotFound(response=self._error_response(environ, 'Static File Not Found: {0}'.format(filepath)))

    def serve_coll_page(self, environ, coll):
        if not self.is_valid_coll(coll):
            raise NotFound(response=self._error_response(environ, 'No handler for "/{0}"'.format(coll)))

        wbrequest = NewWbRequest(environ, '', '/')
        view = BaseInsertView(self.jinja_env, 'search.html')
        content = view.render_to_string(environ, wbrequest=wbrequest)

        return WbResponse.text_response(content, content_type='text/html; charset="utf-8"')

    def serve_listing(self, environ):
        result = {'fixed': self.webagg.list_fixed_routes(),
                  'dynamic': self.webagg.list_dynamic_routes()
                 }

        return WbResponse.json_response(result)

    def is_valid_coll(self, coll):
        return (coll in self.webagg.list_fixed_routes() or
                coll in self.webagg.list_dynamic_routes())

    def serve_content(self, environ, coll='', url=''):
        if not self.is_valid_coll(coll):
            raise NotFound(response=self._error_response(environ, 'No handler for "/{0}"'.format(coll)))

        pop_path_info(environ)
        wb_url = self.get_wburl(environ)

        kwargs = {'coll': coll}

        if coll in self.webagg.list_fixed_routes():
            kwargs['type'] = 'replay-fixed'
        else:
            kwargs['type'] = 'replay-dyn'

        try:
            response = self.render_content(wb_url, kwargs, environ)
        except UpstreamException as ue:
            response = self.handle_error(environ, ue)
            raise HTTPException(response=response)

        return response

    def _check_refer_redirect(self, environ):
        referer = environ.get('HTTP_REFERER')
        if not referer:
            return

        host = environ.get('HTTP_HOST')
        if host not in referer:
            return

        inx = referer[1:].find('http')
        if not inx:
            inx = referer[1:].find('///')
            if inx > 0:
                inx + 1

        if inx < 0:
            return

        url = referer[inx + 1:]
        host = referer[:inx + 1]

        orig_url = environ['PATH_INFO']
        if environ.get('QUERY_STRING'):
            orig_url += '?' + environ['QUERY_STRING']

        full_url = host + urljoin(url, orig_url)
        return WbResponse.redir_response(full_url, '307 Redirect')

    def __call__(self, environ, start_response):
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()

            response = endpoint(environ, **args)

            return response(environ, start_response)

        except HTTPException as e:
            redir = self._check_refer_redirect(environ)
            if redir:
                return redir(environ, start_response)

            return e(environ, start_response)

        except Exception as e:
            if self.debug:
                traceback.print_exc()

            return self._error_response(environ, 'Internal Error: ' + str(e), '500 Server Error')

    @classmethod
    def create_app(cls, port):
        app = FrontEndApp()
        app_server = GeventServer(app, port=port, hostname='0.0.0.0')
        return app_server


# ============================================================================
if __name__ == "__main__":
    app_server = FrontEndApp.create_app(port=8080)
    app_server.join()


