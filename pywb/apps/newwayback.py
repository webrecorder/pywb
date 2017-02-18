from gevent.monkey import patch_all; patch_all()
from pywb.urlrewrite.frontendapp import FrontEndApp

application = FrontEndApp()


