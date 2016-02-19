from pywb.utils.loaders import load_yaml_config

from pywb.framework.archivalrouter import ArchivalRouter, Route
from pywb.framework.proxy import ProxyArchivalRouter
from pywb.framework.wbrequestresponse import WbRequest
from pywb.framework.memento import MementoRequest
from pywb.framework.basehandlers import BaseHandler

from pywb.webapp.views import J2TemplateView
from pywb.webapp.views import J2HtmlCapturesView, init_view

from pywb.webapp.live_rewrite_handler import RewriteHandler

from pywb.webapp.query_handler import QueryHandler
from pywb.webapp.handlers import WBHandler
from pywb.webapp.handlers import StaticHandler
from pywb.webapp.handlers import DebugEchoHandler, DebugEchoEnvHandler
from pywb.webapp.cdx_api_handler import CDXAPIHandler

from pywb import DEFAULT_CONFIG

import os
import logging
import six


#=================================================================
class DictChain(object):
    def __init__(self, *dicts):
        self.dicts = dicts

    def get(self, key, default_val=None):
        for d in self.dicts:
            val = d.get(key)
            if val is not None:
                return val
        return default_val

    def __contains__(self, key):
        return self.get(key) is not None

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.dicts[0][key] = value


#=================================================================
def create_wb_handler(query_handler, config):
    wb_handler_class = config.get('wb_handler_class', WBHandler)

    wb_handler = wb_handler_class(
        query_handler,
        config=config,
    )

    return wb_handler


#=================================================================
def create_live_handler(config):
    wb_handler_class = config.get('wb_handler_class', RewriteHandler)

    live_handler = wb_handler_class(config)

    return live_handler


#=================================================================
def init_route_config(value, config):
    if isinstance(value, str) or isinstance(value, list):
        value = dict(index_paths=value)

    route_config = DictChain(value, config)
    return route_config


#=================================================================
def init_collection(route_config):
    ds_rules_file = route_config.get('domain_specific_rules', None)

    html_view = init_view(route_config, 'query_html', J2HtmlCapturesView)

    server_cls = route_config.get('server_cls')

    query_handler = QueryHandler.init_from_config(route_config,
                                                  ds_rules_file,
                                                  html_view,
                                                  server_cls)

    return query_handler


#=================================================================
def add_cdx_api_handler(name, cdx_api_suffix, routes, query_handler,
                        route_class=Route):
    # if bool, use -cdx suffix, else use custom string
    # as the suffix
    if isinstance(cdx_api_suffix, bool):
        name += '-cdx'
    else:
        name += str(cdx_api_suffix)

    logging.debug('Adding CDX API Handler: ' + name)
    routes.append(route_class(name, CDXAPIHandler(query_handler)))


#=================================================================
def create_cdx_server_app(passed_config):
    """
    Create a cdx server api-only app
    For each collection, create a /<coll>-cdx access point
    which follows the cdx api
    """

    defaults = load_yaml_config(DEFAULT_CONFIG)

    config = DictChain(passed_config, defaults)

    collections = config.get('collections', {})

    static_routes = {}

    # collections based on file system
    if config.get('enable_auto_colls', True):
        colls_loader_cls = config.get('colls_loader_cls', DirectoryCollsLoader)
        dir_loader = colls_loader_cls(config, static_routes, collections)
        dir_loader()
        #collections.update(dir_loader())

    routes = []

    for name, value in six.iteritems(collections):
        route_config = init_route_config(value, config)
        query_handler = init_collection(route_config)

        cdx_api_suffix = route_config.get('enable_cdx_api', True)

        add_cdx_api_handler(name, cdx_api_suffix, routes, query_handler)

    return ArchivalRouter(routes)


#=================================================================
class DirectoryCollsLoader(object):
    def __init__(self, config, static_routes, colls):
        self.config = config
        self.static_routes = static_routes
        self.colls = colls

    def __call__(self):
        colls = self.colls

        static_dir = self.config.get('paths')['static_path']
        static_shared_prefix = self.config.get('static_shared_prefix')

        if static_dir and static_shared_prefix and os.path.isdir(static_dir):
            static_dir = os.path.abspath(static_dir) + os.path.sep
            self.static_routes[static_shared_prefix] = static_dir

        root_dir = self.config.get('collections_root', '')
        if not root_dir or not os.path.isdir(root_dir):
            return colls

        for name in os.listdir(root_dir):
            full = os.path.join(root_dir, name)
            if not os.path.isdir(full):
                continue

            coll_config = self.load_coll_dir(full, name)
            if coll_config:
                # if already exists, override existing config with coll specific
                if name in colls:
                    colls[name].update(coll_config)
                else:
                    colls[name] = coll_config

        return colls

    def _norm_path(self, root_dir, path):
        result = os.path.normpath(os.path.join(root_dir, path))
        return result

    def _add_dir_if_exists(self, coll, root_dir, dir_key, required=False):
        curr_val = coll.get(dir_key)
        if curr_val:
            # add collection path only if relative path, and not a url
            if '://' not in curr_val and not os.path.isabs(curr_val):
                coll[dir_key] = self._norm_path(root_dir, curr_val) + os.path.sep
            return False

        thedir = self.config.get('paths')[dir_key]

        fulldir = os.path.join(root_dir, thedir)

        if os.path.isdir(fulldir):
            fulldir = os.path.abspath(fulldir) + os.path.sep
            coll[dir_key] = fulldir
            return True
        elif required:
            msg = 'Dir "{0}" does not exist for "{1}"'.format(fulldir, dir_key)
            raise Exception(msg)
        else:
            return False

    def load_yaml_file(self, root_dir, filename):
        filename = os.path.join(root_dir, filename)
        if os.path.isfile(filename):
            return load_yaml_config(filename)
        else:
            return {}

    def load_coll_dir(self, root_dir, name):
        # Load config.yaml
        coll_config = self.load_yaml_file(root_dir, 'config.yaml')

        # Load metadata.yaml
        metadata = self.load_yaml_file(root_dir, 'metadata.yaml')
        coll_config['metadata'] = metadata

        self._add_dir_if_exists(coll_config, root_dir, 'index_paths', True)

        # inherit these properties from base, in case archive_paths is shared
        shared_config = DictChain(coll_config, self.config)
        self._add_dir_if_exists(shared_config, root_dir, 'archive_paths', True)

        if self._add_dir_if_exists(coll_config, root_dir, 'static_path', False):
            self.static_routes['static/' + name] = coll_config['static_path']

        # Custom templates dir
        templates_dir = self.config.get('paths').get('templates_dir')
        if templates_dir:
            template_dir = os.path.join(root_dir, templates_dir)

        # Check all templates
        template_files = self.config.get('paths')['template_files']
        for tname, tfile in six.iteritems(template_files):
            if tname in coll_config:
                # Already set
                coll_config[tname] = self._norm_path(root_dir, coll_config[tname])

            # If templates override dir
            elif templates_dir:
                full = os.path.join(template_dir, tfile)
                if os.path.isfile(full):
                    coll_config[tname] = full

        return coll_config


#=================================================================
def create_wb_router(passed_config=None):
    passed_config = passed_config or {}

    defaults = load_yaml_config(DEFAULT_CONFIG)

    config = DictChain(passed_config, defaults)

    routes = []

    port = config.get('port')

    collections = config.get('collections', {})

    static_routes = config.get('static_routes', {})

    root_route = None

    # collections based on file system
    if config.get('enable_auto_colls', True):
        colls_loader_cls = config.get('colls_loader_cls', DirectoryCollsLoader)
        dir_loader = colls_loader_cls(config, static_routes, collections)
        dir_loader()
        #collections.update(dir_loader())

    if config.get('enable_memento', False):
        request_class = MementoRequest
    else:
        request_class = WbRequest

    # store live and replay handlers
    handler_dict = {}

    # setup template globals
    templates_dirs = config['templates_dirs']
    jinja_env = J2TemplateView.init_shared_env(paths=templates_dirs,
                                               packages=config['template_packages'])

    jinja_env.globals.update(config.get('template_globals', {}))

    for static_name, static_path in six.iteritems(static_routes):
        routes.append(Route(static_name, StaticHandler(static_path)))

    for name, value in six.iteritems(collections):
        if isinstance(value, BaseHandler):
            handler_dict[name] = value
            new_route = Route(name, value, config=config)
            if name != '':
                routes.append(new_route)
            else:
                root_route = new_route
            continue

        route_config = init_route_config(value, config)
        route_class = route_config.get('route_class', Route)

        if route_config.get('index_paths') == '$liveweb':
            live = create_live_handler(route_config)
            handler_dict[name] = live
            new_route = route_class(name, live, config=route_config)
            if name != '':
                routes.append(new_route)
            else:
                root_route = new_route
            continue

        query_handler = init_collection(route_config)

        wb_handler = create_wb_handler(
            query_handler=query_handler,
            config=route_config,
        )

        handler_dict[name] = wb_handler

        logging.debug('Adding Collection: ' + name)

        new_route = route_class(name, wb_handler,
                                config=route_config,
                                request_class=request_class)

        if name != '':
            routes.append(new_route)
        else:
            root_route = new_route

        # cdx query handler
        cdx_api_suffix = route_config.get('enable_cdx_api', False)

        if cdx_api_suffix:
            add_cdx_api_handler(name, cdx_api_suffix, routes, query_handler,
                                route_class=route_class)

    if config.get('debug_echo_env', False):
        routes.append(Route('echo_env', DebugEchoEnvHandler()))

    if config.get('debug_echo_req', False):
        routes.append(Route('echo_req', DebugEchoHandler()))

    if root_route:
        routes.append(root_route)

    # resolve any cross handler references
    for route in routes:
        if hasattr(route.handler, 'resolve_refs'):
            route.handler.resolve_refs(handler_dict)

    # default to regular archival mode
    router = ArchivalRouter

    if config.get('enable_http_proxy', False):
        router = ProxyArchivalRouter

        view = init_view(config, 'proxy_select_html')

        if 'proxy_options' not in passed_config:
            passed_config['proxy_options'] = {}

        if view:
            passed_config['proxy_options']['proxy_select_view'] = view

        view = init_view(config, 'proxy_cert_download_html')

        if view:
            passed_config['proxy_options']['proxy_cert_download_view'] = view

    # Finally, create wb router
    return router(
        routes,
        port=port,
        abs_path=config.get('absolute_paths', True),
        home_view=init_view(config, 'home_html'),
        error_view=init_view(config, 'error_html'),
        info_view=init_view(config, 'info_json'),
        config=config
    )
