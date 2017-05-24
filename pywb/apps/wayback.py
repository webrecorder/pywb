from gevent.monkey import patch_all; patch_all()
from pywb.apps.frontendapp import FrontEndApp

application = FrontEndApp()


