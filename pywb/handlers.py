import views
import utils
import urlparse

from wbrequestresponse import WbResponse
from wburl import WbUrl
from wbexceptions import WbException


class BaseHandler:
    @staticmethod
    def get_wburl_type():
        return WbUrl


#=================================================================
# Standard WB Handler
#=================================================================
class WBHandler(BaseHandler):
    def __init__(self, cdx_reader, replay, capturespage = None, searchpage = None):
        self.cdx_reader = cdx_reader
        self.replay = replay

        self.text_view = views.TextCapturesView()
        self.html_view = capturespage
        self.searchpage = searchpage


    def __call__(self, wbrequest):

        if wbrequest.wb_url_str == '/':
            return self.render_searchpage(wbrequest)

        with utils.PerfTimer(wbrequest.env.get('X_PERF'), 'query') as t:
            cdx_lines = self.cdx_reader.load_for_request(wbrequest, parsed_cdx = True)

        # new special modifier to always show cdx index
        if wbrequest.wb_url.mod == 'cdx_':
            return self.text_view.render_response(wbrequest, cdx_lines)

        if (wbrequest.wb_url.type == wbrequest.wb_url.QUERY) or (wbrequest.wb_url.type == wbrequest.wb_url.URL_QUERY):
            query_view = self.html_view if self.html_view else self.text_view
            return query_view.render_response(wbrequest, cdx_lines)

        with utils.PerfTimer(wbrequest.env.get('X_PERF'), 'replay') as t:
            return self.replay(wbrequest, cdx_lines, self.cdx_reader)


    def render_searchpage(self, wbrequest):
        if self.searchpage:
            return self.searchpage.render_response(wbrequest = wbrequest)
        else:
            return WbResponse.text_response('No Lookup Url Specified')



    def __str__(self):
        return 'WBHandler: ' + str(self.cdx_reader) + ', ' + str(self.replay)



#=================================================================
# CDX-Server Handler -- pass all params to cdx server
#=================================================================
class CDXHandler(BaseHandler):
    def __init__(self, cdx_reader, view = None):
        self.cdx_reader = cdx_reader
        self.view = view if view else views.TextCapturesView()

    def __call__(self, wbrequest):
        #url = wbrequest.wb_url.url

        # use url= param to get actual url
        params = urlparse.parse_qs(wbrequest.env['QUERY_STRING'])

        url = params.get('url')
        if not url:
            raise WbException('Must specify a url= param to query cdx server')

        url = url[0]

        cdx_lines = self.cdx_reader.load_cdx(url, params, parsed_cdx = False)

        return self.view.render_response(wbrequest, cdx_lines)


    @staticmethod
    def get_wburl_type():
        return None

#=================================================================
# Debug Handlers
#=================================================================
class DebugEchoEnvHandler(BaseHandler):
    def __call__(self, wbrequest):
        return WbResponse.text_response(str(wbrequest.env))

#=================================================================
class DebugEchoHandler(BaseHandler):
    def __call__(self, wbrequest):
        return WbResponse.text_response(str(wbrequest))



