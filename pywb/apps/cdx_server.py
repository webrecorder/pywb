from pywb.framework.wsgi_wrappers import init_app, start_wsgi_server

#from pywb.core.cdx_api_handler import create_cdx_server_app
from pywb.webapp.pywb_init import create_cdx_server_app

#=================================================================
# init cdx server app
#=================================================================

application = init_app(create_cdx_server_app,
                       load_yaml=True)


def main():  # pragma: no cover
    start_wsgi_server(application, 'CDX Server', default_port=8090)

if __name__ == "__main__":
    main()
