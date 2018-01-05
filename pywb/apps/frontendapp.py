from gevent.monkey import patch_all; patch_all()

#from bottle import run, Bottle, request, response, debug
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import pop_path_info
from six.moves.urllib.parse import urljoin
from six import iteritems

from warcio.utils import to_native_str
from wsgiprox.wsgiprox import WSGIProxMiddleware

from pywb.recorder.multifilewarcwriter import MultiFileWARCWriter
from pywb.recorder.recorderapp import RecorderApp

from pywb.utils.loaders import load_yaml_config
from pywb.utils.geventserver import GeventServer
from pywb.utils.io import StreamIter

from pywb.warcserver.warcserver import WarcServer

from pywb.rewrite.templateview import BaseInsertView

from pywb.apps.static_handler import StaticHandler
from pywb.apps.rewriterapp import RewriterApp, UpstreamException
from pywb.apps.wbrequestresponse import WbResponse

import os
import traceback
import requests
import logging


# ============================================================================
class FrontEndApp(object):
    REPLAY_API = 'http://localhost:%s/{coll}/resource/postreq'
    CDX_API = 'http://localhost:%s/{coll}/index'
    RECORD_SERVER = 'http://localhost:%s'
    RECORD_API = 'http://localhost:%s/%s/resource/postreq?param.recorder.coll={coll}'

    RECORD_ROUTE = '/record'

    PROXY_CA_NAME = 'pywb HTTPS Proxy CA'

    PROXY_CA_PATH = os.path.join('proxy-certs', 'pywb-ca.pem')

    def __init__(self, config_file='./config.yaml', custom_config=None):
        self.handler = self.handle_request
        self.warcserver = WarcServer(config_file=config_file,
                                     custom_config=custom_config)

        config = self.warcserver.config

        self.debug = config.get('debug', False)

        self.warcserver_server = GeventServer(self.warcserver, port=0)

        self.init_proxy(config)

        self.init_recorder(config.get('recorder'))

        self.init_autoindex(config.get('autoindex'))

        static_path = config.get('static_url_path', 'pywb/static/').replace('/', os.path.sep)
        self.static_handler = StaticHandler(static_path)

        self.cdx_api_endpoint = config.get('cdx_api_endpoint', '/cdx')

        self._init_routes()

        upstream_paths = self.get_upstream_paths(self.warcserver_server.port)

        framed_replay = config.get('framed_replay', True)
        self.rewriterapp = RewriterApp(framed_replay,
                                       config=config,
                                       paths=upstream_paths)

        self.templates_dir = config.get('templates_dir', 'templates')
        self.static_dir = config.get('static_dir', 'static')

        metadata_templ = os.path.join(self.warcserver.root_dir, '{coll}', 'metadata.yaml')
        self.metadata_cache = MetadataCache(metadata_templ)

    def _init_routes(self):
        self.url_map = Map()
        self.url_map.add(Rule('/static/_/<coll>/<path:filepath>', endpoint=self.serve_static))
        self.url_map.add(Rule('/static/<path:filepath>', endpoint=self.serve_static))
        self.url_map.add(Rule('/collinfo.json', endpoint=self.serve_listing))

        if self.is_valid_coll('$root'):
            coll_prefix = ''
        else:
            coll_prefix = '/<coll>'
            self.url_map.add(Rule('/', endpoint=self.serve_home))

        self.url_map.add(Rule(coll_prefix + self.cdx_api_endpoint, endpoint=self.serve_cdx))
        self.url_map.add(Rule(coll_prefix + '/', endpoint=self.serve_coll_page))
        self.url_map.add(Rule(coll_prefix + '/timemap/<timemap_output>/<path:url>', endpoint=self.serve_content))

        if self.recorder_path:
            self.url_map.add(Rule(coll_prefix + self.RECORD_ROUTE + '/<path:url>', endpoint=self.serve_record))

        self.url_map.add(Rule(coll_prefix + '/<path:url>', endpoint=self.serve_content))

    def get_upstream_paths(self, port):
        base_paths = {
                'replay': self.REPLAY_API % port,
                'cdx-server': self.CDX_API % port,
               }

        if self.recorder_path:
            base_paths['record'] = self.recorder_path

        return base_paths

    def init_recorder(self, recorder_config):
        if not recorder_config:
            self.recorder = None
            self.recorder_path = None
            return

        if isinstance(recorder_config, str):
            recorder_coll = recorder_config
            recorder_config = {}
        else:
            recorder_coll = recorder_config['source_coll']

        # TODO: support dedup
        dedup_index = None
        warc_writer = MultiFileWARCWriter(self.warcserver.archive_paths,
                                          max_size=int(recorder_config.get('rollover_size', 1000000000)),
                                          max_idle_secs=int(recorder_config.get('rollover_idle_secs', 600)),
                                          filename_template=recorder_config.get('filename_template'),
                                          dedup_index=dedup_index)

        self.recorder = RecorderApp(self.RECORD_SERVER % str(self.warcserver_server.port), warc_writer)

        recorder_server = GeventServer(self.recorder, port=0)

        self.recorder_path = self.RECORD_API % (recorder_server.port, recorder_coll)

    def init_autoindex(self, auto_interval):
        if not auto_interval:
            return

        from pywb.manager.autoindex import AutoIndexer

        colls_dir = self.warcserver.root_dir if self.warcserver.root_dir else None

        indexer = AutoIndexer(colls_dir=colls_dir, interval=int(auto_interval))

        if not os.path.isdir(indexer.root_path):
            msg = 'No managed directory "{0}" for auto-indexing'
            logging.error(msg.format(indexer.root_path))
            import sys
            sys.exit(2)

        msg = 'Auto-Indexing Enabled on "{0}", checking every {1} secs'
        logging.info(msg.format(indexer.root_path, auto_interval))
        indexer.start()

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

    def get_metadata(self, coll):
        #if coll == self.all_coll:
        #    coll = '*'

        metadata = {'coll': coll,
                    'type': 'replay'}

        if coll in self.warcserver.list_fixed_routes():
            metadata.update(self.warcserver.get_coll_config(coll))
        else:
            metadata.update(self.metadata_cache.load(coll))

        return metadata

    def serve_coll_page(self, environ, coll='$root'):
        if not self.is_valid_coll(coll):
            self.raise_not_found(environ, 'No handler for "/{0}"'.format(coll))

        self.setup_paths(environ, coll)

        metadata = self.get_metadata(coll)

        view = BaseInsertView(self.rewriterapp.jinja_env, 'search.html')

        wb_prefix = environ.get('SCRIPT_NAME')
        if wb_prefix:
            wb_prefix += '/'

        content = view.render_to_string(environ,
                                        wb_prefix=wb_prefix,
                                        metadata=metadata,
                                        coll=coll)

        return WbResponse.text_response(content, content_type='text/html; charset="utf-8"')

    def serve_cdx(self, environ, coll='$root'):
        base_url = self.rewriterapp.paths['cdx-server']

        #if coll == self.all_coll:
        #    coll = '*'

        cdx_url = base_url.format(coll=coll)

        if environ.get('QUERY_STRING'):
            cdx_url += '&' if '?' in cdx_url else '?'
            cdx_url += environ.get('QUERY_STRING')

        try:
            res = requests.get(cdx_url, stream=True)

            content_type = res.headers.get('Content-Type')

            return WbResponse.bin_stream(StreamIter(res.raw),
                                         content_type=content_type)

        except Exception as e:
            return WbResponse.text_response('Error: ' + str(e), status='400 Bad Request')

    def serve_record(self, environ, coll='$root', url=''):
        if coll in self.warcserver.list_fixed_routes():
            return WbResponse.text_response('Error: Can Not Record Into Custom Collection "{0}"'.format(coll))

        return self.serve_content(environ, coll, url, record=True)

    def serve_content(self, environ, coll='$root', url='', timemap_output='', record=False):
        if not self.is_valid_coll(coll):
            self.raise_not_found(environ, 'No handler for "/{0}"'.format(coll))

        self.setup_paths(environ, coll, record)

        wb_url_str = to_native_str(url)

        if environ.get('QUERY_STRING'):
            wb_url_str += '?' + environ.get('QUERY_STRING')

        metadata = self.get_metadata(coll)
        if record:
            metadata['type'] = 'record'

        if timemap_output:
            metadata['output'] = timemap_output

        try:
            response = self.rewriterapp.render_content(wb_url_str, metadata, environ)
        except UpstreamException as ue:
            response = self.rewriterapp.handle_error(environ, ue)
            raise HTTPException(response=response)

        return response

    def setup_paths(self, environ, coll, record=False):
        if not coll or not self.warcserver.root_dir:
            return

        if coll != '$root':
            pop_path_info(environ)
            if record:
                pop_path_info(environ)

        paths = [self.warcserver.root_dir]

        if coll != '$root':
            paths.append(coll)

        paths.append(self.templates_dir)

        # jinja2 template paths always use '/' as separator
        environ['pywb.templates_dir'] = '/'.join(paths)

    def serve_listing(self, environ):
        result = {'fixed': self.warcserver.list_fixed_routes(),
                  'dynamic': self.warcserver.list_dynamic_routes()
                 }

        return WbResponse.json_response(result)

    def is_valid_coll(self, coll):
        #if coll == self.all_coll:
        #    return True

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
        return self.handler(environ, start_response)

    def handle_request(self, environ, start_response):
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

    def init_proxy(self, config):
        proxy_config = config.get('proxy')
        if not proxy_config:
            return

        if isinstance(proxy_config, str):
            proxy_coll = proxy_config
            proxy_config = {}
        else:
            proxy_coll = proxy_config['coll']

        if '/' in proxy_coll:
            raise Exception('Proxy collection can not contain "/"')

        proxy_config['ca_name'] = proxy_config.get('ca_name', self.PROXY_CA_NAME)
        proxy_config['ca_file_cache'] = proxy_config.get('ca_file_cache', self.PROXY_CA_PATH)

        if proxy_config.get('recording'):
            logging.info('Proxy recording into collection "{0}"'.format(proxy_coll))
            if proxy_coll in self.warcserver.list_fixed_routes():
                raise Exception('Can not record into fixed collection')

            proxy_coll += self.RECORD_ROUTE
            if not config.get('recorder'):
                config['recorder'] = 'live'

        else:
            logging.info('Proxy enabled for collection "{0}"'.format(proxy_coll))

        prefix = '/{0}/bn_/'.format(proxy_coll)

        self.handler = WSGIProxMiddleware(self.handle_request, prefix,
                                  proxy_host=proxy_config.get('host', 'pywb.proxy'),
                                  proxy_options=proxy_config)


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


