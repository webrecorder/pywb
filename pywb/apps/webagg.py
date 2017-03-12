from gevent.monkey import patch_all; patch_all()
from pywb.webagg.autoapp import AutoConfigApp

application = AutoConfigApp(custom_config={'collections': {'live': '$live'}})



