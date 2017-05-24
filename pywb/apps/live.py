from gevent.monkey import patch_all; patch_all()
from pywb.apps.frontendapp import FrontEndApp

application = FrontEndApp(config_file=None,
                          custom_config={'collections': {'live': '$live'}})


