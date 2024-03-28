from gevent.monkey import patch_all; patch_all()

from werkzeug.routing import Map, Rule, RequestRedirect, Submount
from wsgiref.util import shift_path_info
from six.moves.urllib.parse import urljoin, parse_qsl
from six import iteritems
from warcio.utils import to_native_str
from warcio.timeutils import iso_date_to_timestamp, timestamp_to_iso_date
from wsgiprox.wsgiprox import WSGIProxMiddleware

from pywb.recorder.multifilewarcwriter import MultiFileWARCWriter
from pywb.recorder.recorderapp import RecorderApp
from pywb.recorder.filters import SkipDupePolicy, WriteDupePolicy, WriteRevisitDupePolicy
from pywb.recorder.redisindexer import WritableRedisIndexer, RedisPendingCounterTempBuffer

from pywb.utils.loaders import load_yaml_config
from pywb.utils.geventserver import GeventServer
from pywb.utils.io import StreamIter
from pywb.utils.wbexception import WbException, AppPageNotFound

from pywb.warcserver.warcserver import WarcServer

from pywb.rewrite.templateview import BaseInsertView

from pywb.apps.static_handler import StaticHandler
from pywb.apps.rewriterapp import RewriterApp
from pywb.apps.wbrequestresponse import WbResponse

import os
import re

import traceback
import requests
import logging


# ============================================================================
class FrontEndApp(object):
    """Orchestrates pywb's core Wayback Machine functionality and is comprised of 2 core sub-apps and 3 optional apps.

    Sub-apps:
      - WarcServer: Serves the archive content (WARC/ARC and index) as well as from the live web in record/proxy mode
      - RewriterApp: Rewrites the content served by pywb (if it is to be rewritten)
      - WSGIProxMiddleware (Optional): If proxy mode is enabled, performs pywb's HTTP(s) proxy functionality
      - AutoIndexer (Optional): If auto-indexing is enabled for the collections it is started here
      - RecorderApp (Optional): Recording functionality, available when recording mode is enabled

    The RewriterApp is configurable and can be set via the class var `REWRITER_APP_CLS`, defaults to RewriterApp
    """

    REPLAY_API = 'http://localhost:%s/{coll}/resource/postreq'
    CDX_API = 'http://localhost:%s/{coll}/index'
    RECORD_SERVER = 'http://localhost:%s'
    RECORD_API = 'http://localhost:%s/%s/resource/postreq?param.recorder.coll={coll}'

    RECORD_ROUTE = '/record'

    PROXY_CA_NAME = 'pywb HTTPS Proxy CA'

    PROXY_CA_PATH = os.path.join('proxy-certs', 'pywb-ca.pem')

    REWRITER_APP_CLS = RewriterApp

    ALL_DIGITS = re.compile(r'^\d+$')

    def __init__(self, config_file=None, custom_config=None):
        """
        :param str|None config_file: Path to the config file
        :param dict|None custom_config: Dictionary containing additional configuration information
        """
        config_file = config_file or './config.yaml'
        self.handler = self.handle_request
        self.warcserver = WarcServer(config_file=config_file,
                                     custom_config=custom_config)
        self.recorder = None
        self.recorder_path = None
        self.put_custom_record_path = None
        self.proxy_default_timestamp = None

        config = self.warcserver.config

        self.debug = config.get('debug', False)

        self.warcserver_server = GeventServer(self.warcserver, port=0)

        self.proxy_prefix = None  # the URL prefix to be used for the collection with proxy mode (e.g. /coll/id_/)
        self.proxy_coll = None  # the name of the collection that has proxy mode enabled
        self.proxy_record = False # indicate if proxy recording
        self.init_proxy(config)

        self.init_recorder(config.get('recorder'))

        self.init_autoindex(config.get('autoindex'))

        static_path = config.get('static_url_path', 'pywb/static/').replace('/', os.path.sep)
        self.static_handler = StaticHandler(static_path)

        self.cdx_api_endpoint = config.get('cdx_api_endpoint', '/cdx')
        self.query_limit = config.get('query_limit')

        upstream_paths = self.get_upstream_paths(self.warcserver_server.port)

        framed_replay = config.get('framed_replay', True)
        self.rewriterapp = self.REWRITER_APP_CLS(framed_replay,
                                                 config=config,
                                                 paths=upstream_paths)

        self.templates_dir = config.get('templates_dir', 'templates')
        self.static_dir = config.get('static_dir', 'static')
        self.static_prefix = config.get('static_prefix', 'static')
        self.default_locale = config.get('default_locale', '')

        metadata_templ = os.path.join(self.warcserver.root_dir, '{coll}', 'metadata.yaml')
        self.metadata_cache = MetadataCache(metadata_templ)

        self._init_routes()

    def _init_routes(self):
        """Initialize the routes and based on the configuration file makes available
        specific routes (proxy mode, record)
        """
        self.url_map = Map()
        self.url_map.add(Rule('/{0}/_/<coll>/<path:filepath>'.format(self.static_prefix), endpoint=self.serve_static))
        self.url_map.add(Rule('/{0}/<path:filepath>'.format(self.static_prefix), endpoint=self.serve_static))
        self.url_map.add(Rule('/collinfo.json', endpoint=self.serve_listing))

        if self.is_valid_coll('$root'):
            coll_prefix = ''
        else:
            coll_prefix = '/<coll>'
            self.url_map.add(Rule('/', endpoint=self.serve_home))

        self._init_coll_routes(coll_prefix)

        if self.proxy_prefix is not None:
            # Add the proxy-fetch endpoint to enable PreservationWorker to make CORS fetches worry free in proxy mode
            self.url_map.add(Rule('/proxy-fetch/<path:url>', endpoint=self.proxy_fetch,
                                  methods=['GET', 'HEAD', 'OPTIONS']))

    def _init_coll_routes(self, coll_prefix):
        """Initialize and register the routes for specified collection path

        :param str coll_prefix: The collection path
        :rtype: None
        """
        routes = self._make_coll_routes(coll_prefix)

        # init loc routes, if any
        loc_keys = list(self.rewriterapp.loc_map.keys())
        if loc_keys:
            routes.append(Rule('/', endpoint=self.serve_home))

            submount_route = ', '.join(loc_keys)
            submount_route = '/<any({0}):lang>'.format(submount_route)

            self.url_map.add(Submount(submount_route, routes))

        for route in routes:
            self.url_map.add(route)

    def _make_coll_routes(self, coll_prefix):
        """Creates a list of standard collection routes for the
        specified collection path

        :param str coll_prefix: The collection path
        :return: A list of route rules for the supplied collection
        :rtype: list[Rule]
        """
        routes = [
            Rule(coll_prefix + self.cdx_api_endpoint, endpoint=self.serve_cdx),
            Rule(coll_prefix + '/', endpoint=self.serve_coll_page),
            Rule(coll_prefix + '/timemap/<timemap_output>/<path:url>', endpoint=self.serve_content),
            Rule(coll_prefix + '/<path:url>', endpoint=self.serve_content)
        ]

        if self.recorder_path:
            routes.append(Rule(coll_prefix + self.RECORD_ROUTE + '/<path:url>', endpoint=self.serve_record))

            # enable PUT of custom data as 'resource' records
            if self.put_custom_record_path:
                routes.append(Rule(coll_prefix + self.RECORD_ROUTE, endpoint=self.put_custom_record, methods=["PUT"]))

        return routes

    def get_upstream_paths(self, port):
        """Retrieve a dictionary containing the full URLs of the upstream apps

        :param int port: The port used by the replay and cdx servers
        :return: A dictionary containing the upstream paths (replay, cdx-server, record [if enabled])
        :rtype: dict[str, str]
        """
        base_paths = {
            'replay': self.REPLAY_API % port,
            'cdx-server': self.CDX_API % port,
        }

        if self.recorder_path:
            base_paths['record'] = self.recorder_path

        return base_paths

    def init_recorder(self, recorder_config):
        """Initialize the recording functionality of pywb. If recording_config is None this function is a no op

        :param str|dict|None recorder_config: The configuration for the recorder app
        :rtype: None
        """
        if not recorder_config:
            self.recorder = None
            self.recorder_path = None
            return

        if isinstance(recorder_config, str):
            recorder_coll = recorder_config
            recorder_config = {}
        else:
            recorder_coll = recorder_config['source_coll']

        # cache mode
        self.rec_cache_mode = recorder_config.get('cache', 'default')

        dedup_policy = recorder_config.get('dedup_policy')
        dedup_by_url = False

        if dedup_policy == 'none':
            dedup_policy = ''

        if dedup_policy == 'keep':
            dedup_policy = WriteDupePolicy()
        elif dedup_policy == 'revisit':
            dedup_policy = WriteRevisitDupePolicy()
        elif dedup_policy == 'skip':
            dedup_policy = SkipDupePolicy()
            dedup_by_url = True
        elif dedup_policy:
            msg = 'Invalid option for dedup_policy: {0}'
            raise Exception(msg.format(dedup_policy))

        if dedup_policy:
            dedup_index = WritableRedisIndexer(redis_url=self.warcserver.dedup_index_url,
                                               dupe_policy=dedup_policy,
                                               rel_path_template=self.warcserver.root_dir + '/{coll}/archive')
        else:
            dedup_index = None


        warc_writer = MultiFileWARCWriter(self.warcserver.archive_paths,
                                          max_size=int(recorder_config.get('rollover_size', 1000000000)),
                                          max_idle_secs=int(recorder_config.get('rollover_idle_secs', 600)),
                                          filename_template=recorder_config.get('filename_template'),
                                          dedup_index=dedup_index,
                                          dedup_by_url=dedup_by_url)

        if dedup_policy:
            pending_counter = self.warcserver.dedup_index_url.replace(':cdxj', ':pending')
            pending_timeout = recorder_config.get('pending_timeout', 30)
            create_buff_func = lambda params, name: RedisPendingCounterTempBuffer(512 * 1024, pending_counter, params, name, pending_timeout)
        else:
            create_buff_func = None

        self.recorder = RecorderApp(self.RECORD_SERVER % str(self.warcserver_server.port), warc_writer,
                                    accept_colls=recorder_config.get('source_filter'),
                                    create_buff_func=create_buff_func)

        recorder_server = GeventServer(self.recorder, port=0)

        self.recorder_path = self.RECORD_API % (recorder_server.port, recorder_coll)

        # enable PUT of custom data as 'resource' records
        if recorder_config.get('enable_put_custom_record'):
            self.put_custom_record_path = self.recorder_path + '&put_record={rec_type}&url={url}'

    def init_autoindex(self, auto_interval):
        """Initialize and start the auto-indexing of the collections. If auto_interval is None this is a no op.

        :param str|int auto_interval: The auto-indexing interval from the configuration file or CLI argument
        """
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

    def is_proxy_enabled(self, environ):
        """Returns T/F indicating if proxy mode is enabled

        :param dict environ: The WSGI environment dictionary for the request
        :return: T/F indicating if proxy mode is enabled
        :rtype: bool
        """
        return self.proxy_prefix is not None and 'wsgiprox.proxy_host' in environ

    def serve_home(self, environ):
        """Serves the home (/) view of pywb (not a collections)

        :param dict environ: The WSGI environment dictionary for the request
        :return: The WbResponse for serving the home (/) path
        :rtype: WbResponse
        """
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
        """Serve a static file associated with a specific collection or one of pywb's own static assets

        :param dict environ: The WSGI environment dictionary for the request
        :param str coll: The collection the static file is associated with
        :param str filepath: The file path (relative to the collection) for the static assest
        :return: The WbResponse for the static asset
        :rtype: WbResponse
        """
        proxy_enabled = self.is_proxy_enabled(environ)
        if proxy_enabled and environ.get('REQUEST_METHOD') == 'OPTIONS':
            return WbResponse.options_response(environ)
        if coll:
            path = os.path.join(self.warcserver.root_dir, coll, self.static_dir)
        else:
            path = self.static_dir

        environ['pywb.static_dir'] = path
        try:
            response = self.static_handler(environ, filepath)
            if proxy_enabled:
                response.add_access_control_headers(env=environ)
            return response
        except Exception:
            self.raise_not_found(environ, 'static_file_not_found', filepath)

    def get_coll_config(self, coll):
        """Retrieve the collection config, including metadata, associated with a collection

        :param str coll: The name of the collection to receive config info for
        :return: The collections config
        :rtype: dict
        """
        coll_config = {'coll': coll,
                       'type': 'replay'}

        if coll in self.warcserver.list_fixed_routes():
            coll_config.update(self.warcserver.get_coll_config(coll))
        else:
            coll_config['metadata'] = self.metadata_cache.load(coll) or {}

        if 'ui' in self.warcserver.config:
            coll_config['ui'] = self.warcserver.config['ui']

        return coll_config

    def serve_coll_page(self, environ, coll='$root'):
        """Render and serve a collections search page (search.html).

        :param dict environ: The WSGI environment dictionary for the request
        :param str coll: The name of the collection to serve the collections search page for
        :return: The WbResponse containing the collections search page
        :rtype: WbResponse
        """
        if not self.is_valid_coll(coll):
            self.raise_not_found(environ, 'coll_not_found', coll)

        self.setup_paths(environ, coll)

        coll_config = self.get_coll_config(coll)
        metadata = coll_config.get('metadata')
        ui = coll_config.get('ui', {})

        view = BaseInsertView(self.rewriterapp.jinja_env, 'search.html')

        wb_prefix = environ.get('SCRIPT_NAME', '')
        if wb_prefix:
            wb_prefix += '/'

        content = view.render_to_string(environ,
                                        wb_prefix=wb_prefix,
                                        coll=coll,
                                        coll_config=coll_config,
                                        metadata=metadata,
                                        ui=ui)

        return WbResponse.text_response(content, content_type='text/html; charset="utf-8"')

    def serve_cdx(self, environ, coll='$root'):
        """Make the upstream CDX query for a collection and response with the results of the query

        :param dict environ: The WSGI environment dictionary for the request
        :param str coll: The name of the collection this CDX query is for
        :return: The WbResponse containing the results of the CDX query
        :rtype: WbResponse
        """
        base_url = self.rewriterapp.paths['cdx-server']

        # if coll == self.all_coll:
        #    coll = '*'

        config = self.warcserver.get_coll_config(coll)
        is_live = config.get("index") == "$live"

        if is_live:
            cache_control = "no-store, no-cache"
        else:
            cache_control = "max-age=86400, must-revalidate"

        cdx_url = base_url.format(coll=coll)

        if environ.get('QUERY_STRING'):
            cdx_url += '&' if '?' in cdx_url else '?'
            cdx_url += environ.get('QUERY_STRING')

        if self.query_limit:
            cdx_url += '&' if '?' in cdx_url else '?'
            cdx_url += 'limit=' + str(self.query_limit)

        try:
            headers = {}
            for key in environ.keys():
                if key.startswith("HTTP_X_"):
                    headers[key[5:].replace("_", "-")] = environ[key]
            res = requests.get(cdx_url, stream=True, headers=headers)

            status_line = '{} {}'.format(res.status_code, res.reason)
            content_type = res.headers.get('Content-Type')

            return WbResponse.bin_stream(StreamIter(res.raw),
                                         content_type=content_type,
                                         status=status_line,
                                         headers=[("Cache-Control", cache_control)])

        except Exception as e:
            return WbResponse.text_response('Error: ' + str(e), status='400 Bad Request')

    def serve_record(self, environ, coll='$root', url=''):
        """Serve a URL's content from a WARC/ARC record in replay mode or from the live web in
        live, proxy, and record mode.

        :param dict environ: The WSGI environment dictionary for the request
        :param str coll: The name of the collection the record is to be served from
        :param str url: The URL for the corresponding record to be served if it exists
        :return: WbResponse containing the contents of the record/URL
        :rtype: WbResponse
        """
        if coll in self.warcserver.list_fixed_routes():
            return WbResponse.text_response('Error: Can Not Record Into Custom Collection "{0}"'.format(coll))

        return self.serve_content(environ, coll, url, record=True)

    def serve_content(self, environ, coll='$root', url='', timemap_output='', record=False):
        """Serve the contents of a URL/Record rewriting the contents of the response when applicable.

        :param dict environ: The WSGI environment dictionary for the request
        :param str coll: The name of the collection the record is to be served from
        :param str url: The URL for the corresponding record to be served if it exists
        :param str timemap_output: The contents of the timemap included in the link header of the response
        :param bool record: Should the content being served by recorded (save to a warc). Only valid in record mode
        :return: WbResponse containing the contents of the record/URL
        :rtype: WbResponse
        """
        if not self.is_valid_coll(coll):
            self.raise_not_found(environ, 'coll_not_found', coll)

        self.setup_paths(environ, coll, record)

        request_uri = environ.get('REQUEST_URI')
        script_name = environ.get('SCRIPT_NAME', '') + '/'
        if request_uri and request_uri.startswith(script_name):
            wb_url_str = request_uri[len(script_name):]

        else:
            wb_url_str = to_native_str(url)

            if environ.get('QUERY_STRING'):
                wb_url_str += '?' + environ.get('QUERY_STRING')

        coll_config = self.get_coll_config(coll)
        if record:
            coll_config['type'] = 'record'
            coll_config['cache'] = self.rec_cache_mode

        if timemap_output:
            coll_config['output'] = timemap_output
            # ensure that the timemap path information is not included
            wb_url_str = wb_url_str.replace('timemap/{0}/'.format(timemap_output), '')

        return self.rewriterapp.render_content(wb_url_str, coll_config, environ)

    def put_custom_record(self, environ, coll="$root"):
        """ When recording, PUT a custom WARC record to the specified collection
        (Available only when recording)

        :param dict environ: The WSGI environment dictionary for the request
        :param str coll: The name of the collection the record is to be served from
        """
        chunks = []
        while True:
            buff = environ["wsgi.input"].read()
            if not buff:
                break

            chunks.append(buff)

        data = b"".join(chunks)

        params = dict(parse_qsl(environ.get("QUERY_STRING")))

        rec_type = "resource"

        headers = {"Content-Type": environ.get("CONTENT_TYPE", "text/plain")}

        target_uri = params.get("url")

        if not target_uri:
            return WbResponse.json_response({"error": "no url"}, status="400 Bad Request")

        timestamp = params.get("timestamp")
        if timestamp:
            headers["WARC-Date"] = timestamp_to_iso_date(timestamp)

        put_url = self.put_custom_record_path.format(
            url=target_uri, coll=coll, rec_type=rec_type
        )
        res = requests.put(put_url, headers=headers, data=data)

        res = res.json()

        return WbResponse.json_response(res)

    def setup_paths(self, environ, coll, record=False):
        """Populates the WSGI environment dictionary with the path information necessary to perform a response for
        content or record.

        :param dict environ: The WSGI environment dictionary for the request
        :param str coll: The name of the collection the record is to be served from
        :param bool record: Should the content being served by recorded (save to a warc). Only valid in record mode
        """
        if not coll or not self.warcserver.root_dir:
            return

        if coll != '$root':
            shift_path_info(environ)
            if record:
                shift_path_info(environ)

        paths = [self.warcserver.root_dir]

        if coll != '$root':
            paths.append(coll)

        paths.append(self.templates_dir)

        # jinja2 template paths always use '/' as separator
        environ['pywb.templates_dir'] = '/'.join(paths)

    def serve_listing(self, environ):
        """Serves the response for WARCServer fixed and dynamic listing (paths)

        :param dict environ: The WSGI environment dictionary for the request
        :return: WbResponse containing the frontend apps WARCServer URL paths
        :rtype: WbResponse
        """
        result = {'fixed': self.warcserver.list_fixed_routes(),
                  'dynamic': self.warcserver.list_dynamic_routes()
                  }

        return WbResponse.json_response(result)

    def is_valid_coll(self, coll):
        """Determines if the collection name for a request is valid (exists)

        :param str coll: The name of the collection to check
        :return: True if the collection is valid, false otherwise
        :rtype: bool
        """
        # if coll == self.all_coll:
        #    return True

        return (coll in self.warcserver.list_fixed_routes() or
                coll in self.warcserver.list_dynamic_routes())

    def raise_not_found(self, environ, err_type, url):
        """Utility function for raising a werkzeug.exceptions.NotFound execption with the supplied WSGI environment
        and message.

        :param dict environ: The WSGI environment dictionary for the request
        :param str err_type: The identifier for type of error that occurred
        :param str url: The url of the archived page that was requested
        """
        raise AppPageNotFound(err_type, url)

    def _check_refer_redirect(self, environ):
        """Returns a WbResponse for a HTTP 307 redirection if the HTTP referer header is the same as the HTTP host header

        :param dict environ: The WSGI environment dictionary for the request
        :return: WbResponse HTTP 307 redirection
        :rtype: WbResponse
        """
        referer = environ.get('HTTP_REFERER')
        if not referer:
            return

        host = environ.get('HTTP_HOST')
        if host not in referer:
            return

        inx = referer[1:].find('http')
        if not inx:
            inx = referer[1:].find('///')

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
        """Handles a request

        :param dict environ: The WSGI environment dictionary for the request
        :param start_response:
        :return: The WbResponse for the request
        :rtype: WbResponse
        """
        return self.handler(environ, start_response)

    def handle_request(self, environ, start_response):
        """Retrieves the route handler and calls the handler returning its the response

        :param dict environ: The WSGI environment dictionary for the request
        :param start_response:
        :return: The WbResponse for the request
        :rtype: WbResponse
        """
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()

            self.rewriterapp.prepare_env(environ)

            # store original script_name (original prefix) before modifications are made
            environ['ORIG_SCRIPT_NAME'] = environ.get('SCRIPT_NAME')

            lang = args.pop('lang', '')
            if lang:
                shift_path_info(environ)

            if lang:
                environ['pywb_lang'] = lang
            elif self.default_locale:
                environ['pywb_lang'] = self.default_locale

            response = endpoint(environ, **args)

        except RequestRedirect as rr:
            # if werkzeug throws this, likely a missing slash redirect
            # also check referrer here to avoid another redirect later
            redir = self._check_refer_redirect(environ)
            if redir:
                return redir(environ, start_response)

            response = WbResponse.redir_response(rr.new_url, '307 Redirect')

        except WbException as wbe:
            if wbe.status_code == 404:
                redir = self._check_refer_redirect(environ)
                if redir:
                    return redir(environ, start_response)

            response = self.rewriterapp.handle_error(environ, wbe)

        except Exception as e:
            if self.debug:
                traceback.print_exc()

            response = self.rewriterapp._error_response(environ, WbException('Internal Error: ' + str(e)))

        return response(environ, start_response)

    @classmethod
    def create_app(cls, port):
        """Create a new instance of FrontEndApp that listens on port with a hostname of 0.0.0.0

        :param int port: The port FrontEndApp is to listen on
        :return: A new instance of FrontEndApp wrapped in GeventServer
        :rtype: GeventServer
        """
        app = FrontEndApp()
        app_server = GeventServer(app, port=port, hostname='0.0.0.0')
        return app_server

    def init_proxy(self, config):
        """Initialize and start proxy mode. If proxy configuration entry is not contained in the config
        this is a no op. Causes handler to become an instance of WSGIProxMiddleware.

        :param dict config: The configuration object used to configure this instance of FrontEndApp
        """
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

            proxy_route = proxy_coll + self.RECORD_ROUTE
            if not config.get('recorder'):
                config['recorder'] = 'live'

            self.proxy_record = True

        else:
            logging.info('Proxy enabled for collection "{0}"'.format(proxy_coll))
            self.proxy_record = False
            proxy_route = proxy_coll

        if proxy_config.get('enable_content_rewrite', True):
            self.proxy_prefix = '/{0}/bn_/'.format(proxy_route)
        else:
            self.proxy_prefix = '/{0}/id_/'.format(proxy_route)

        self.proxy_default_timestamp = proxy_config.get('default_timestamp')
        if self.proxy_default_timestamp:
            if not self.ALL_DIGITS.match(self.proxy_default_timestamp):
                try:
                    self.proxy_default_timestamp = iso_date_to_timestamp(self.proxy_default_timestamp)
                except Exception:
                    raise Exception('Invalid Proxy Timestamp: Must Be All-Digit Timestamp or ISO Date Format')

        self.proxy_coll = proxy_coll

        self.handler = WSGIProxMiddleware(self.handle_request,
                                          self.proxy_route_request,
                                          proxy_host=proxy_config.get('host', 'pywb.proxy'),
                                          proxy_options=proxy_config)

    def proxy_route_request(self, url, environ):
        """ Return the full url that this proxy request will be routed to
        The 'environ' PATH_INFO and REQUEST_URI will be modified based on the returned url

        Default is to use the 'proxy_prefix' to point to the proxy collection
        """
        if self.proxy_default_timestamp:
            environ['pywb_proxy_default_timestamp'] = self.proxy_default_timestamp

        return self.proxy_prefix + url

    def proxy_fetch(self, env, url):
        """Proxy mode only endpoint that handles OPTIONS requests and COR fetches for Preservation Worker.

        Due to normal cross-origin browser restrictions in proxy mode, auto fetch worker cannot access the CSS rules
        of cross-origin style sheets and must re-fetch them in a manner that is CORS safe. This endpoint facilitates
        that by fetching the stylesheets for the auto fetch worker and then responds with its contents

        :param dict env: The WSGI environment dictionary
        :param str url:  The URL of the resource to be fetched
        :return: WbResponse that is either response to an Options request or the results of fetching url
        :rtype: WbResponse
        """
        if not self.is_proxy_enabled(env):
            # we are not in proxy mode so just respond with forbidden
            return WbResponse.text_response('proxy mode must be enabled to use this endpoint',
                                            status='403 Forbidden')

        if env.get('REQUEST_METHOD') == 'OPTIONS':
            return WbResponse.options_response(env)

        # ensure full URL
        url = env['REQUEST_URI'].split('/proxy-fetch/', 1)[-1]

        env['REQUEST_URI'] = self.proxy_prefix + url
        env['PATH_INFO'] = self.proxy_prefix + env['PATH_INFO'].split('/proxy-fetch/', 1)[-1]

        # make request using normal serve_content
        response = self.serve_content(env, self.proxy_coll, url, record=self.proxy_record)

        # for WR
        if isinstance(response, WbResponse):
            response.add_access_control_headers(env=env)
        return response


# ============================================================================
class MetadataCache(object):
    """This class holds the collection medata template string and
    caches the metadata for a collection once it is rendered once.
    Cached metadata is updated if its corresponding file has been updated since last cache time (file mtime based)"""

    def __init__(self, template_str):
        """
        :param str template_str: The template string to be cached
        """
        self.template_str = template_str
        self.cache = {}

    def load(self, coll):
        """Load and receive the metadata associated with a collection.

        If the metadata for the collection is not cached yet its metadata file is read in and stored.
        If the cache has seen the collection before the mtime of the metadata file is checked and if it is more recent
        than the cached time, the cache is updated and returned otherwise the cached version is returned.

        :param str coll: Name of a collection
        :return: The cached metadata for a collection
        :rtype: dict
        """
        path = self.template_str.format(coll=coll)
        try:
            mtime = os.path.getmtime(path)
            obj = self.cache.get(path)
        except Exception:
            return {}

        if not obj:
            return self.store_new(coll, path, mtime)

        cached_mtime, data = obj
        if mtime == cached_mtime == mtime:
            return obj

        return self.store_new(coll, path, mtime)

    def store_new(self, coll, path, mtime):
        """Load a collections metadata file and store it

        :param str coll: The name of the collection the metadata is for
        :param str path: The path to the collections metadata file
        :param float mtime: The current mtime of the collections metadata file
        :return: The collections metadata
        :rtype: dict
        """
        obj = load_yaml_config(path)
        self.cache[coll] = (mtime, obj)
        return obj

    def get_all(self, routes):
        """Load the metadata for all routes (collections) and populate the cache

        :param list[str] routes: List of collection names
        :return: A dictionary containing each collections metadata
        :rtype: dict
        """
        for route in routes:
            self.load(route)

        return {name: value[1] for name, value in iteritems(self.cache)}


# ============================================================================
if __name__ == "__main__":
    app_server = FrontEndApp.create_app(port=8080)
    app_server.join()
