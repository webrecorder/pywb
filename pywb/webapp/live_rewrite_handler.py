from pywb.framework.basehandlers import WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.archivalrouter import ArchivalRouter, Route

from pywb.rewrite.rewrite_live import LiveRewriter
from pywb.rewrite.wburl import WbUrl

from handlers import StaticHandler, SearchPageWbUrlHandler
from views import HeadInsertView

from pywb.utils.wbexception import WbException


#=================================================================
class LiveResourceException(WbException):
    def status(self):
        return '400 Bad Live Resource'


#=================================================================
class RewriteHandler(SearchPageWbUrlHandler):
    def __init__(self, config):
        super(RewriteHandler, self).__init__(config)

        default_proxy = config.get('proxyhostport')
        self.rewriter = LiveRewriter(is_framed_replay=self.is_frame_mode,
                                     default_proxy=default_proxy)

        self.head_insert_view = HeadInsertView.init_from_config(config)

    def handle_request(self, wbrequest):
        try:
            return self.render_content(wbrequest)

        except Exception as exc:
            url = wbrequest.wb_url.url
            msg = 'Could not load the url from the live web: ' + url
            #raise LiveResourceException(msg=msg, url=url)
            raise

    def _live_request_headers(self, wbrequest):
        return {}

    def render_content(self, wbrequest):
        head_insert_func = self.head_insert_view.create_insert_func(wbrequest)
        req_headers = self._live_request_headers(wbrequest)

        ref_wburl_str = wbrequest.extract_referrer_wburl_str()
        if ref_wburl_str:
            wbrequest.env['REL_REFERER'] = WbUrl(ref_wburl_str).url

        wb_url = wbrequest.wb_url
        result = self.rewriter.fetch_request(wb_url, wbrequest.urlrewriter,
                                             head_insert_func=head_insert_func,
                                             req_headers=req_headers,
                                             env=wbrequest.env)

        return self._make_response(wbrequest, *result)

    def _make_response(self, wbrequest, status_headers, gen, is_rewritten):
        cdx = wbrequest.env['pywb.cdx']
        cookie = 'pywb.timestamp=' + cdx['timestamp'] + '; max-age=60'
        status_headers.headers.append(('Set-Cookie', cookie))

        return WbResponse(status_headers, gen)

    def __str__(self):
        return 'Live Web Rewrite Handler'


#=================================================================
def create_live_rewriter_app(config={}):
    routes = [Route('rewrite', RewriteHandler(config)),
              Route('static/default', StaticHandler('pywb/static/'))
             ]

    return ArchivalRouter(routes, hostpaths=['http://localhost:8080'])
