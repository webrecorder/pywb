from gevent.monkey import patch_all; patch_all()
from pywb.warcserver.warcserver import WarcServer

application = WarcServer(custom_config={'collections': {'live': '$live'}})



