from pywb.framework.wsgi_wrappers import init_app, start_wsgi_server

from pywb.webapp.live_rewrite_handler import create_live_rewriter_app

#=================================================================
# init cdx server app
#=================================================================

application = init_app(create_live_rewriter_app, load_yaml=False)


def main():  # pragma: no cover
    start_wsgi_server(application, 'Live Rewriter App', default_port=8090)

if __name__ == "__main__":
    main()
