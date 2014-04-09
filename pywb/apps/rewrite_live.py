from pywb.framework.wsgi_wrappers import init_app, start_wsgi_server

from pywb.webapp.rewrite_handler import create_rewrite_app

#=================================================================
# init cdx server app
#=================================================================

application = init_app(create_rewrite_app, load_yaml=False)


def main():  # pragma: no cover
    start_wsgi_server(application, 'Rewrite App', default_port=8090)

if __name__ == "__main__":
    main()
