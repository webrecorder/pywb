from pywb.framework.archivalrouter import ArchivalRouter, Route
from pywb.framework.proxy import ProxyArchivalRouter

from pywb.warc.recordloader import ArcWarcRecordLoader
from pywb.warc.resolvingloader import ResolvingLoader

from pywb.rewrite.rewrite_content import RewriteContent

from pywb.cdx.cdxserver import create_cdx_server

from indexreader import IndexReader
from views import J2TemplateView, J2HtmlCapturesView
from replay_views import ReplayView

from handlers import WBHandler
from handlers import StaticHandler
from cdx_handler import CDXHandler
from handlers import DebugEchoHandler, DebugEchoEnvHandler


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

    'static_routes': {'static/default': 'static/'},

    'domain_specific_rules': 'pywb/rules.yaml',
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
def load_template_file(file, desc=None, view_class=J2TemplateView):
    if file:
        logging.debug('Adding {0}: {1}'.format(desc if desc else name, file))
        file = view_class(file)

    return file


#=================================================================
def create_wb_handler(cdx_server, config, ds_rules_file=None):

    cookie_maker=config.get('cookie_maker')
    record_loader = ArcWarcRecordLoader(cookie_maker=cookie_maker)

    paths = config.get('archive_paths')

    resolving_loader = ResolvingLoader(paths=paths,
                                       record_loader=record_loader)

    head_insert_view = load_template_file(config.get('head_insert_html'),
                                          'Head Insert')

    replayer = ReplayView(
        content_loader=resolving_loader,

        content_rewriter=RewriteContent(ds_rules_file=ds_rules_file),

        head_insert_view=head_insert_view,

        buffer_response=config.get('buffer_response', True),

        redir_to_exact=config.get('redir_to_exact', True),

        reporter=config.get('reporter')
    )

    html_view = load_template_file(config.get('query_html'),
                                   'Captures Page',
                                   J2HtmlCapturesView)


    search_view = load_template_file(config.get('search_html'),
                                     'Search Page')

    wb_handler = WBHandler(
        cdx_server,
        replayer,
        html_view=html_view,
        search_view=search_view,
    )

    return wb_handler


#=================================================================
def create_wb_router(passed_config = {}):

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

    for name, value in collections.iteritems():
        if isinstance(value, str):
            value = {'index_paths': value}

        route_config = DictChain(value, config)

        ds_rules_file = route_config.get('domain_specific_rules', None)

        perms_policy = route_config.get('perms_policy', None)

        cdx_server = create_cdx_server(route_config,
                                       ds_rules_file)

        cdx_server = IndexReader(cdx_server, perms_policy)

        wb_handler = create_wb_handler(
            cdx_server=cdx_server,
            config=route_config,
            ds_rules_file=ds_rules_file,
        )

        logging.debug('Adding Collection: ' + name)

        route_class = route_config.get('route_class', Route)

        routes.append(route_class(name, wb_handler, config = route_config))

        # cdx query handler
        if route_config.get('enable_cdx_api', False):
            routes.append(Route(name + '-cdx', CDXHandler(cdx_server)))


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
        # This will help catch occasionally missed rewrites that fall-through to the host
        # (See archivalrouter.ReferRedirect)
        hostpaths = hostpaths,
        port = port,

        abs_path = config.get('absolute_paths', True),

        home_view = load_template_file(config.get('home_html'), 'Home Page'),
        error_view = load_template_file(config.get('error_html'), 'Error Page')
    )
