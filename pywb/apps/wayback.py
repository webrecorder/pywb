from pywb.framework.wsgi_wrappers import init_app
from pywb.webapp.pywb_init import create_wb_router


#=================================================================
# init pywb app
#=================================================================
application = init_app(create_wb_router, load_yaml=True)
