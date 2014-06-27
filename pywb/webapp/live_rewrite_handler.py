from pywb.framework.basehandlers import WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.archivalrouter import ArchivalRouter, Route
from pywb.rewrite.rewriterules import use_lxml_parser

from handlers import StaticHandler

from replay_views import RewriteLiveView


#=================================================================
class RewriteHandler(WbUrlHandler):
    def __init__(self, config=dict(framed_replay=True)):
        self.rewrite_view = RewriteLiveView(config)

    def __call__(self, wbrequest):
        return self.rewrite_view(wbrequest)


#=================================================================
def create_live_rewriter_app():
    routes = [Route('rewrite', RewriteHandler()),
              Route('static/default', StaticHandler('pywb/static/'))
             ]

#    use_lxml_parser()
    return ArchivalRouter(routes, hostpaths=['http://localhost:8080'])
