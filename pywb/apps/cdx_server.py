from pywb.cdx.cdxserver import create_cdx_server

from pywb.framework.wsgi_wrappers import init_app, start_wsgi_server
from pywb.framework.archivalrouter import ArchivalRouter, Route

from pywb.core.handlers import CDXHandler

DEFAULT_RULES = 'pywb/rules.yaml'

# cdx-server only config
DEFAULT_CONFIG = 'pywb/cdx/config.yaml'

#=================================================================
# create simple cdx server under '/cdx' using config file
# TODO: support multiple collections like full wayback?

def create_cdx_server_app(config):
    cdx_server = create_cdx_server(config, DEFAULT_RULES)
    routes = [Route('cdx', CDXHandler(cdx_server))]
    return ArchivalRouter(routes)

#=================================================================
# init pywb app
#=================================================================
application = init_app(create_cdx_server_app,
                       load_yaml=True,
                       config_file=DEFAULT_CONFIG)

if __name__ == "__main__":
    start_wsgi_server(application)
