from pywb.framework.basehandlers import WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.archivalrouter import ArchivalRouter, Route

from handlers import StaticHandler, SearchPageWbUrlHandler

from replay_views import RewriteLiveView

from pywb.utils.wbexception import WbException


#=================================================================
class LiveResourceException(WbException):
    def status(self):
        return '400 Bad Live Resource'


#=================================================================
class RewriteHandler(SearchPageWbUrlHandler):
    def __init__(self, config):
        super(RewriteHandler, self).__init__(config)
        self.rewrite_view = RewriteLiveView(config)

    def __call__(self, wbrequest):
        if wbrequest.wb_url_str == '/':
            return self.render_search_page(wbrequest)

        try:
            return self.rewrite_view(wbrequest)

        except Exception as exc:
            url = wbrequest.wb_url.url
            msg = 'Could not load the url from the live web: ' + url
            raise LiveResourceException(msg=msg, url=url)

    def __str__(self):
        return 'Live Web Rewrite Handler'


#=================================================================
def create_live_rewriter_app(config={}):
    routes = [Route('rewrite', RewriteHandler(config)),
              Route('static/default', StaticHandler('pywb/static/'))
             ]

    return ArchivalRouter(routes, hostpaths=['http://localhost:8080'])
