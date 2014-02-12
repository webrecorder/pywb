import views
import utils
import urlparse

from wbrequestresponse import WbResponse
from wburl import WbUrl
from wbexceptions import WbException, NotFoundException

import pkgutil
import mimetypes


class BaseHandler:
    @staticmethod
    def get_wburl_type():
        return WbUrl

    def __call__(self, wbrequest):
        return wbrequest

#=================================================================
# Standard WB Handler
#=================================================================
class WBHandler(BaseHandler):
    def __init__(self, cdx_reader, replay, html_view = None, search_view = None):
        self.cdx_reader = cdx_reader
        self.replay = replay

        self.text_view = views.TextCapturesView()

        self.html_view = html_view
        self.search_view = search_view


    def __call__(self, wbrequest):

        if wbrequest.wb_url_str == '/':
            return self.render_search_page(wbrequest)

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


    def render_search_page(self, wbrequest):
        if self.search_view:
            return self.search_view.render_response(wbrequest = wbrequest)
        else:
            return WbResponse.text_response('No Lookup Url Specified')


    def __str__(self):
        return 'WBHandler: ' + str(self.cdx_reader) + ', ' + str(self.replay)

#=================================================================
# CDX-Server Handler -- pass all params to cdx server
#=================================================================
class CDXHandler(BaseHandler):
    def __init__(self, cdx_server, view = None):
        self.cdx_server = cdx_server
        self.view = view if view else views.TextCapturesView()

    def __call__(self, wbrequest):
        cdx_lines = self.cdx_server.load_cdx_from_request(wbrequest.env)

        return self.view.render_response(wbrequest, cdx_lines)


    @staticmethod
    def get_wburl_type():
        return None

    def __str__(self):
        return 'CDX Server: ' + str(self.cdx_server)


#=================================================================
# Static Content Handler
#=================================================================
class StaticHandler(BaseHandler):
    def __init__(self, static_path, pkg = __package__):
        mimetypes.init()

        self.static_path = static_path
        self.pkg = pkg

    def __call__(self, wbrequest):
        full_path = self.static_path + wbrequest.wb_url_str

        try:
            if full_path.startswith('.') or full_path.startswith('file://'):
                data = open(full_path, 'rb')
            else:
                data = pkgutil.get_data(self.pkg, full_path)

            if 'wsgi.file_wrapper' in wbrequest.env:
                reader = wbrequest.env['wsgi.file_wrapper'](data)
            else:
                reader = iter(lambda: data.read(), '')

            content_type, _ = mimetypes.guess_type(full_path)

            return WbResponse.text_stream(data, content_type = content_type)

        except IOError:
            raise NotFoundException('Static File Not Found: ' + wbrequest.wb_url_str)

    @staticmethod
    def get_wburl_type():
        return None

    def __str__(self):
        return 'Static files from ' + self.static_path


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



