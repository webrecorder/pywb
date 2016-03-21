import os

if os.environ.get('GEVENT_MONKEY_PATCH') == '1':  #pragma: no cover
    # Use gevent if available
    try:
        from gevent.monkey import patch_all; patch_all()
        print('gevent patched!')
    except Exception as e:
        pass

from pywb.framework.wsgi_wrappers import init_app
from pywb.webapp.pywb_init import create_wb_router


#=================================================================
# init pywb app
#=================================================================
application = init_app(create_wb_router, load_yaml=True)
