from pywb.utils.dsrules import DEFAULT_RULES_FILE

from pywb.framework.archivalrouter import ArchivalRouter, Route
from pywb.framework.proxy import ProxyArchivalRouter
from pywb.framework.wbrequestresponse import WbRequest
from pywb.framework.memento import MementoRequest
from pywb.framework.basehandlers import BaseHandler

from pywb.warc.recordloader import ArcWarcRecordLoader
from pywb.warc.resolvingloader import ResolvingLoader

from pywb.rewrite.rewrite_content import RewriteContent
from pywb.rewrite.rewriterules import use_lxml_parser

from views import J2TemplateView, add_env_globals
from views import J2HtmlCapturesView, HeadInsertView

from replay_views import ReplayView

from query_handler import QueryHandler
from handlers import WBHandler
from handlers import StaticHandler
from handlers import DebugEchoHandler, DebugEchoEnvHandler
from cdx_api_handler import CDXAPIHandler


import os
import logging


#=================================================================
DEFAULTS = {
    'hostpaths':  ['http://localhost:8080'],
    'collections': {'pywb': './sample_archive/cdx/'},
    'archive_paths': './sample_archive/warcs/',

    'head_insert_html': 'ui/head_insert.html',
    'query_html': 'ui/query.html',
    'search_html': 'ui/search.html',
    'home_html': 'ui/index.html',
    'error_html': 'ui/error.html',

    'template_globals': {'static_path': 'static/default'},

    'static_routes': {'static/default': 'pywb/static/'},

    'domain_specific_rules': DEFAULT_RULES_FILE,

    'enable_memento': True,

    'use_lxml_parser': True,
}


#=================================================================
class DictChain:
    def __init__(self, *dicts):
        self.dicts = dicts

    def get(self, key, default_val=None):
        for d in self.dicts:
            val = d.get(key)
            if val is not None:
                return val
        return default_val


#=================================================================
def create_wb_handler(query_handler, config,
                      ds_rules_file=DEFAULT_RULES_FILE):

    cookie_maker = config.get('cookie_maker')
    record_loader = ArcWarcRecordLoader(cookie_maker=cookie_maker)

    paths = config.get('archive_paths')

    resolving_loader = ResolvingLoader(paths=paths,
                                       record_loader=record_loader)

    template_globals = config.get('template_globals')
    if template_globals:
        add_env_globals(template_globals)

    head_insert_view = (HeadInsertView.
                        create_template(config.get('head_insert_html'),
                                       'Head Insert'))

    defmod = config.get('default_mod', '')

    replayer = ReplayView(
        content_loader=resolving_loader,

        content_rewriter=RewriteContent(ds_rules_file=ds_rules_file,
                                        defmod=defmod),

        head_insert_view=head_insert_view,

        buffer_response=config.get('buffer_response', True),

        redir_to_exact=config.get('redir_to_exact', True),

        memento=config.get('enable_memento', False),

        reporter=config.get('reporter')
    )

    search_view = (J2TemplateView.
                   create_template(config.get('search_html'),
                                   'Search Page'))

    wb_handler_class = config.get('wb_handler_class', WBHandler)

    wb_handler = wb_handler_class(
        query_handler,
        replayer,
        search_view=search_view,
        config=config,
    )

    return wb_handler


#=================================================================
def init_collection(value, config):
    if isinstance(value, str):
        value = {'index_paths': value}

    route_config = DictChain(value, config)

    ds_rules_file = route_config.get('domain_specific_rules', None)

    html_view = (J2HtmlCapturesView.
                 create_template(config.get('query_html'),
                                 'Captures Page'))

    query_handler = QueryHandler.init_from_config(route_config,
                                                  ds_rules_file,
                                                  html_view)

    return route_config, query_handler, ds_rules_file


#=================================================================
def add_cdx_api_handler(name, cdx_api_suffix, routes, query_handler):
    # if bool, use -cdx suffix, else use custom string
    # as the suffix
    if isinstance(cdx_api_suffix, bool):
        name += '-cdx'
    else:
        name += str(cdx_api_suffix)

    routes.append(Route(name, CDXAPIHandler(query_handler)))


#=================================================================
def create_cdx_server_app(passed_config):
    """
    Create a cdx server api-only app
    For each collection, create a /<coll>-cdx access point
    which follows the cdx api
    """
    config = DictChain(passed_config, DEFAULTS)

    collections = config.get('collections')

    routes = []

    for name, value in collections.iteritems():
        result = init_collection(value, config)
        route_config, query_handler, ds_rules_file = result

        cdx_api_suffix = route_config.get('enable_cdx_api', True)

        add_cdx_api_handler(name, cdx_api_suffix, routes, query_handler)

    return ArchivalRouter(routes)


#=================================================================
def create_wb_router(passed_config={}):

    config = DictChain(passed_config, DEFAULTS)

    routes = []

    # TODO: examine this more
    hostname = os.environ.get('PYWB_HOST_NAME')
    if hostname:
        hostpaths = [hostname]
    else:
        hostpaths = config.get('hostpaths')

    port = config.get('port')

    # collections based on cdx source
    collections = config.get('collections')

    if config.get('enable_memento', False):
        request_class = MementoRequest
    else:
        request_class = WbRequest

    if config.get('use_lxml_parser', False):
        use_lxml_parser()

    for name, value in collections.iteritems():

        if isinstance(value, BaseHandler):
            routes.append(Route(name, value))
            continue

        result = init_collection(value, config)
        route_config, query_handler, ds_rules_file = result

        wb_handler = create_wb_handler(
            query_handler=query_handler,
            config=route_config,
            ds_rules_file=ds_rules_file,
        )

        logging.debug('Adding Collection: ' + name)

        route_class = route_config.get('route_class', Route)

        routes.append(route_class(name, wb_handler,
                                  config=route_config,
                                  request_class=request_class))

        # cdx query handler
        cdx_api_suffix = route_config.get('enable_cdx_api', False)

        if cdx_api_suffix:
            add_cdx_api_handler(name, cdx_api_suffix, routes, query_handler)

    if config.get('debug_echo_env', False):
        routes.append(Route('echo_env', DebugEchoEnvHandler()))

    if config.get('debug_echo_req', False):
        routes.append(Route('echo_req', DebugEchoHandler()))

    static_routes = config.get('static_routes')

    for static_name, static_path in static_routes.iteritems():
        routes.append(Route(static_name, StaticHandler(static_path)))

    # Check for new proxy mode!
    if config.get('enable_http_proxy', False):
        router = ProxyArchivalRouter
    else:
        router = ArchivalRouter

    # Finally, create wb router
    return router(
        routes,
        # Specify hostnames that pywb will be running on
        # This will help catch occasionally missed rewrites that
        # fall-through to the host
        # (See archivalrouter.ReferRedirect)
        hostpaths=hostpaths,
        port=port,

        abs_path=config.get('absolute_paths', True),

        home_view=J2TemplateView.create_template(config.get('home_html'),
                                                 'Home Page'),

        error_view=J2TemplateView.create_template(config.get('error_html'),
                                                 'Error Page')
    )
