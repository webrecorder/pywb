from pywb.framework.basehandlers import WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.archivalrouter import ArchivalRouter, Route

from handlers import StaticHandler

from replay_views import RewriteLiveView


#=================================================================
class RewriteHandler(WbUrlHandler):
    def __init__(self, config):
        self.rewrite_view = RewriteLiveView(config)

    def __call__(self, wbrequest):
        return self.rewrite_view(wbrequest)

    def __str__(self):
        return 'Live Web Rewrite Handler'


#=================================================================
def create_live_rewriter_app(config={}):
    routes = [Route('rewrite', RewriteHandler(config)),
              Route('static/default', StaticHandler('pywb/static/'))
             ]

    return ArchivalRouter(routes, hostpaths=['http://localhost:8080'])
