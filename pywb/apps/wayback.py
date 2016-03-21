import sys

if not hasattr(sys, '_called_from_test'):  #pragma: no cover
    # Use gevent if available
    try:
        from gevent.monkey import patch_all; patch_all()
    except Exception as e:
        pass

from pywb.framework.wsgi_wrappers import init_app
from pywb.webapp.pywb_init import create_wb_router


#=================================================================
# init pywb app
#=================================================================
application = init_app(create_wb_router, load_yaml=True)
