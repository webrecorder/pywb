from gevent.monkey import patch_all; patch_all()

#from bottle import run, Bottle, request, response, debug
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import pop_path_info
from six.moves.urllib.parse import urljoin
from six import iteritems

from warcio.utils import to_native_str

from pywb.utils.loaders import load_yaml_config
from pywb.utils.geventserver import GeventServer

from pywb.warcserver.warcserver import WarcServer

from pywb.rewrite.templateview import BaseInsertView

from pywb.apps.static_handler import StaticHandler
from pywb.apps.rewriterapp import RewriterApp, UpstreamException
from pywb.apps.wbrequestresponse import WbResponse

import os
import traceback


# ============================================================================
class FrontEndApp(object):
    def __init__(self, config_file='./config.yaml', custom_config=None):
        self.debug = True
        self.warcserver = WarcServer(config_file=config_file,
                                     custom_config=custom_config)

        framed_replay = self.warcserver.config.get('framed_replay', True)

        self.rewriterapp = RewriterApp(framed_replay, config=self.warcserver.config)

        self.warcserver_server = GeventServer(self.warcserver, port=0)

        self.static_handler = StaticHandler('pywb/static/')

        self.url_map = Map()
        self.url_map.add(Rule('/static/_/<coll>/<path:filepath>', endpoint=self.serve_static))
        self.url_map.add(Rule('/static/<path:filepath>', endpoint=self.serve_static))
        self.url_map.add(Rule('/<coll>/', endpoint=self.serve_coll_page))
        self.url_map.add(Rule('/<coll>/<path:url>', endpoint=self.serve_content))
        self.url_map.add(Rule('/collinfo.json', endpoint=self.serve_listing))
        self.url_map.add(Rule('/', endpoint=self.serve_options, methods=['OPTIONS']))
        self.url_map.add(Rule('/', endpoint=self.serve_home))

        self.rewriterapp.paths = self.get_upstream_paths(self.warcserver_server.port)

        self.templates_dir = self.warcserver.config.get('templates_dir', 'templates')
        self.static_dir = self.warcserver.config.get('static_dir', 'static')

        metadata_templ = os.path.join(self.warcserver.root_dir, '{coll}', 'metadata.yaml')
        self.metadata_cache = MetadataCache(metadata_templ)

    def get_upstream_paths(self, port):
        return {'replay-dyn': 'http://localhost:%s/_/resource/postreq?param.coll={coll}' % port,
                'replay-fixed': 'http://localhost:%s/{coll}/resource/postreq' % port
               }

    def serve_home(self, environ):
        home_view = BaseInsertView(self.rewriterapp.jinja_env, 'index.html')
        fixed_routes = self.warcserver.list_fixed_routes()
        dynamic_routes = self.warcserver.list_dynamic_routes()

        routes = fixed_routes + dynamic_routes

        all_metadata = self.metadata_cache.get_all(dynamic_routes)

        content = home_view.render_to_string(environ,
                                             routes=routes,
                                             all_metadata=all_metadata)

        return WbResponse.text_response(content, content_type='text/html; charset="utf-8"')

    def serve_options(self, environ):
        return WbResponse.options_response(environ)

    def serve_static(self, environ, coll='', filepath=''):
        if coll:
            path = os.path.join(self.warcserver.root_dir, coll, self.static_dir)
        else:
            path = self.static_dir

        environ['pywb.static_dir'] = path

        try:
            return self.static_handler(environ, filepath)
        except:
            self.raise_not_found(environ, 'Static File Not Found: {0}'.format(filepath))

    def serve_coll_page(self, environ, coll):
        if not self.is_valid_coll(coll):
            self.raise_not_found(environ, 'No handler for "/{0}"'.format(coll))

        self.setup_paths(environ, coll)

        metadata = self.metadata_cache.load(coll)

        view = BaseInsertView(self.rewriterapp.jinja_env, 'search.html')

        content = view.render_to_string(environ,
                                        wb_prefix=environ.get('SCRIPT_NAME') + '/',
                                        metadata=metadata)

        return WbResponse.text_response(content, content_type='text/html; charset="utf-8"')

    def serve_content(self, environ, coll='', url=''):
        if not self.is_valid_coll(coll):
            self.raise_not_found(environ, 'No handler for "/{0}"'.format(coll))

        self.setup_paths(environ, coll)

        wb_url_str = to_native_str(url)

        if environ.get('QUERY_STRING'):
            wb_url_str += '?' + environ.get('QUERY_STRING')

        kwargs = {'coll': coll}

        if coll in self.warcserver.list_fixed_routes():
            kwargs['type'] = 'replay-fixed'
        else:
            kwargs['type'] = 'replay-dyn'

        try:
            response = self.rewriterapp.render_content(wb_url_str, kwargs, environ)
        except UpstreamException as ue:
            response = self.rewriterapp.handle_error(environ, ue)
            raise HTTPException(response=response)

        return response

    def setup_paths(self, environ, coll):
        pop_path_info(environ)
        if not coll or not self.warcserver.root_dir:
            return

        environ['pywb.templates_dir'] = os.path.join(self.warcserver.root_dir,
                                                     coll,
                                                     self.templates_dir)

    def serve_listing(self, environ):
        result = {'fixed': self.warcserver.list_fixed_routes(),
                  'dynamic': self.warcserver.list_dynamic_routes()
                 }

        return WbResponse.json_response(result)

    def is_valid_coll(self, coll):
        return (coll in self.warcserver.list_fixed_routes() or
                coll in self.warcserver.list_dynamic_routes())

    def raise_not_found(self, environ, msg):
        raise NotFound(response=self.rewriterapp._error_response(environ, msg))

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

            response = self.rewriterapp._error_response(environ, 'Internal Error: ' + str(e), '500 Server Error')
            return response(environ, start_response)

    @classmethod
    def create_app(cls, port):
        app = FrontEndApp()
        app_server = GeventServer(app, port=port, hostname='0.0.0.0')
        return app_server


# ============================================================================
class MetadataCache(object):
    def __init__(self, template_str):
        self.template_str = template_str
        self.cache = {}

    def load(self, coll):
        path = self.template_str.format(coll=coll)
        try:
            mtime = os.path.getmtime(path)
            obj = self.cache.get(path)
        except:
            return {}

        if not obj:
            return self.store_new(coll, path, mtime)

        cached_mtime, data = obj
        if mtime == cached_mtime == mtime:
            return obj

        return self.store_new(coll, path, mtime)

    def store_new(self, coll, path, mtime):
        obj = load_yaml_config(path)
        self.cache[coll] = (mtime, obj)
        return obj

    def get_all(self, routes):
        for route in routes:
            self.load(route)

        return {name: value[1] for name, value in iteritems(self.cache)}


# ============================================================================
if __name__ == "__main__":
    app_server = FrontEndApp.create_app(port=8080)
    app_server.join()


