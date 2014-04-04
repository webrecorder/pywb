from pywb.framework.wsgi_wrappers import init_app, start_wsgi_server
from pywb.webapp.pywb_init import create_wb_router

#=================================================================
# init pywb app
#=================================================================
application = init_app(create_wb_router, load_yaml=True)


def main():  # pragma: no cover
    start_wsgi_server(application, 'Wayback')

if __name__ == "__main__":
    main()
