import handlers
import indexreader
import archivalrouter
import os
import yaml
import config_utils
import logging
import proxy

#=================================================================
## Reference non-YAML config
#=================================================================
def pywb_config_manual(config = {}):

    routes = []

    hostpaths = config.get('hostpaths', ['http://localhost:8080/'])

    # collections based on cdx source
    collections = config.get('collections', {'pywb': './sample_archive/cdx/'})

    for name, value in collections.iteritems():
        if isinstance(value, dict):
            # if a dict, extend with base properies
            index_paths = value['index_paths']
            value.extend(config)
            config = value
        else:
            index_paths = str(value)

        cdx_source = indexreader.IndexReader.make_best_cdx_source(index_paths, **config)

        # cdx query handler
        if config.get('enable_cdx_api', False):
            routes.append(archivalrouter.Route(name + '-cdx', handlers.CDXHandler(cdx_source)))

        wb_handler = config_utils.create_wb_handler(
            cdx_source = cdx_source,
            archive_paths = config.get('archive_paths', './sample_archive/warcs/'),
            head_html = config.get('head_insert_html'),
            query_html = config.get('query_html'),
            search_html = config.get('search_html'),
            static_path = config.get('static_path', hostpaths[0] + 'static/')
        )

        logging.info('Adding Collection: ' + name)

        routes.append(archivalrouter.Route(name, wb_handler))


    if config.get('debug_echo_env', False):
        routes.append(archivalrouter.Route('echo_env', handlers.DebugEchoEnvHandler()))

    if config.get('debug_echo_req', False):
        routes.append(archivalrouter.Route('echo_req', handlers.DebugEchoHandler()))

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


import utils
if __name__ == "__main__" or utils.enable_doctests():
    # Just test for execution for now
    #pywb_config(os.path.dirname(os.path.realpath(__file__)) + '/../config.yaml')
    pywb_config_manual()


