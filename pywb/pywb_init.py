import handlers
import archivalrouter
import config_utils
import proxy
from indexreader import IndexReader

import os
import yaml
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
}

class DictChain:
    def __init__(self, *dicts):
        self.dicts = dicts

    def get(self, key, default_val=None):
        for d in self.dicts:
            val = d.get(key)
            if val:
                return val
        return default_val


#=================================================================
## Reference non-YAML config
#=================================================================
def pywb_config_manual(passed_config = {}):

    config = DictChain(passed_config, DEFAULTS)

    routes = []

    hostpaths = config.get('hostpaths')

    # collections based on cdx source
    collections = config.get('collections')

    for name, value in collections.iteritems():
        if isinstance(value, str):
            route_config = config
            cdx_server = IndexReader(value)
        else:
            route_config = DictChain(value, config)
            cdx_server = IndexReader(route_config)


        wb_handler = config_utils.create_wb_handler(
            cdx_server = cdx_server,
            config = route_config,
        )

        logging.debug('Adding Collection: ' + name)

        route_class = route_config.get('route_class', archivalrouter.Route)

        routes.append(route_class(name, wb_handler, config = route_config))

        # cdx query handler
        if route_config.get('enable_cdx_api', False):
            routes.append(archivalrouter.Route(name + '-cdx', handlers.CDXHandler(cdx_server)))


    if config.get('debug_echo_env', False):
        routes.append(archivalrouter.Route('echo_env', handlers.DebugEchoEnvHandler()))

    if config.get('debug_echo_req', False):
        routes.append(archivalrouter.Route('echo_req', handlers.DebugEchoHandler()))


    static_routes = config.get('static_routes')

    for static_name, static_path in static_routes.iteritems():
        routes.append(archivalrouter.Route(static_name, handlers.StaticHandler(static_path)))

    # Check for new proxy mode!
    if config.get('enable_http_proxy', False):
        router = proxy.ProxyArchivalRouter
    else:
        router = archivalrouter.ArchivalRouter

    # Finally, create wb router
    return router(
        routes,
        # Specify hostnames that pywb will be running on
        # This will help catch occasionally missed rewrites that fall-through to the host
        # (See archivalrouter.ReferRedirect)
        hostpaths = hostpaths,

        abs_path = config.get('absolute_paths', True),

        home_view = config_utils.load_template_file(config.get('home_html'), 'Home Page'),
        error_view = config_utils.load_template_file(config.get('error_html'), 'Error Page')
    )



#=================================================================
# YAML config loader
#=================================================================
DEFAULT_CONFIG_FILE = 'config.yaml'


def pywb_config(config_file = None):
    if not config_file:
        config_file = os.environ.get('PYWB_CONFIG', DEFAULT_CONFIG_FILE)

    config = yaml.load(open(config_file))

    return pywb_config_manual(config)

