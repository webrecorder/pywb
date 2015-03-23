from pywb.framework.wsgi_wrappers import init_app

#from pywb.core.cdx_api_handler import create_cdx_server_app
from pywb.webapp.pywb_init import create_cdx_server_app

#=================================================================
# init cdx server app
#=================================================================

application = init_app(create_cdx_server_app,
                       load_yaml=True)
