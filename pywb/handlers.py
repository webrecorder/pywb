import views
import utils
import urlparse

#=================================================================
# Standard WB Handler
#=================================================================
class WBHandler:
    def __init__(self, cdx_reader, replay, html_view = None):
        self.cdx_reader = cdx_reader
        self.replay = replay
        self.html_view = html_view
        self.text_view = views.TextQueryView()

    def __call__(self, wbrequest):
        with utils.PerfTimer(wbrequest.env.get('X_PERF'), 'query') as t:
            cdx_lines = self.cdx_reader.load_for_request(wbrequest, parsed_cdx = True)

        # new special modifier to always show cdx index
        if wbrequest.wb_url.mod == 'cdx_':
            return self.text_view(wbrequest, cdx_lines)

        if (wbrequest.wb_url.type == wbrequest.wb_url.QUERY) or (wbrequest.wb_url.type == wbrequest.wb_url.URL_QUERY):
            if not self.html_view:
                return self.text_view(wbrequest, cdx_lines)
            else:
                return self.html_view(wbrequest, cdx_lines)

        with utils.PerfTimer(wbrequest.env.get('X_PERF'), 'replay') as t:
            return self.replay(wbrequest, cdx_lines, self.cdx_reader)



#=================================================================
# CDX-Server Handler -- pass all params to cdx server
#=================================================================
class CDXHandler:
    def __init__(self, cdx_reader, view = None):
        self.cdx_reader = cdx_reader
        self.view = view if view else views.TextQueryView()

    def __call__(self, wbrequest):
        url = wbrequest.wb_url.url

        # use url= param to get actual url
        params = urlparse.parse_qs(wbrequest.env['QUERY_STRING'])

        url = params.get('url')
        if not url:
            raise Exception('Must specify a url= param to query cdx server')

        url = url[0]

        cdx_lines = self.cdx_reader.load_cdx(url, params, parsed_cdx = False)

        return self.view(wbrequest, cdx_lines)


#=================================================================
# Debug Handlers
#=================================================================
class DebugEchoEnvHandler:
    def __call__(self, wbrequest):
        return wbrequestresponse.WbResponse.text_response(str(wbrequest.env))

#=================================================================
class DebugEchoHandler:
    def __call__(self, wbrequest):
        return wbrequestresponse.WbResponse.text_response(str(wbrequest))



