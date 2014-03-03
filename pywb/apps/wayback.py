from pywb.bootstrap.wsgi_wrappers import init_app, start_wsgi_server
from pywb.bootstrap.pywb_init import create_wb_router

#=================================================================
# init pywb app
#=================================================================
application = init_app(create_wb_router, load_yaml=True)

if __name__ == "__main__":
    start_wsgi_server(application)
