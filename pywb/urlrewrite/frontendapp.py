from gevent.monkey import patch_all; patch_all()

#from bottle import run, Bottle, request, response, debug
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from werkzeug.wsgi import pop_path_info

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
        self.user_metadata = {}


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
        self.url_map.add(Rule('/_coll_info.json', endpoint=self.serve_listing))

        self.paths = self.get_upstream_paths(self.webagg_server.port)

    def get_upstream_paths(self, port):
        return {'replay-dyn': 'http://localhost:%s/_/resource/postreq?param.coll={coll}' % port,
                'replay-fixed': 'http://localhost:%s/{coll}/resource/postreq' % port
               }

    def serve_static(self, environ, filepath=''):
        return self.static_handler(NewWbRequest(environ, filepath, ''))

    def serve_coll_page(self, environ, coll):
        view = BaseInsertView(self.jinja_env, 'search.html')
        wbrequest = NewWbRequest(environ, '', '/')
        return WbResponse.text_response(view.render_to_string(environ, wbrequest=wbrequest),
                                        content_type='text/html; charset="utf-8"')

    def serve_listing(self, environ):
        result = {'fixed': self.webagg.list_fixed_routes(),
                  'dynamic': self.webagg.list_dynamic_routes()
                 }

        return WbResponse.json_response(result)

    def serve_content(self, environ, coll='', url=''):
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

        return response

    def __call__(self, environ, start_response):
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
        except HTTPException as e:
            return e(environ, start_response)

        try:
            response = endpoint(environ, **args)

            return response(environ, start_response)

        except Exception as e:
            if self.debug:
                traceback.print_exc()

            #message = 'Internal Error: ' + str(e)
            #status = 500
            #return self.send_error({}, start_response,
            #                       message=message,
            #                       status=status)

    @classmethod
    def create_app(cls, port):
        app = FrontEndApp()
        app_server = GeventServer(app, port=port, hostname='0.0.0.0')
        return app_server


# ============================================================================
if __name__ == "__main__":
    app_server = FrontEndApp.create_app(port=8080)
    app_server.join()


