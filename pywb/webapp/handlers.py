import pkgutil
import mimetypes
import time

from datetime import datetime

from pywb.utils.wbexception import NotFoundException
from pywb.utils.loaders import BlockLoader
from pywb.utils.statusandheaders import StatusAndHeaders

from pywb.framework.basehandlers import BaseHandler, WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse

from pywb.warc.recordloader import ArcWarcRecordLoader
from pywb.warc.resolvingloader import ResolvingLoader

from views import J2TemplateView
from replay_views import ReplayView
from pywb.framework.memento import MementoResponse
from pywb.utils.timeutils import datetime_to_timestamp


#=================================================================
class SearchPageWbUrlHandler(WbUrlHandler):
    """
    Loads a default search page html template to be shown when
    the wb_url is empty
    """
    def __init__(self, config):
        self.search_view = (J2TemplateView.
                            create_template(config.get('search_html'),
                           'Search Page'))

        self.is_frame_mode = config.get('framed_replay', False)
        self.response_class = WbResponse

        if self.is_frame_mode:
            html = config.get('frame_insert_html', 'templates/frame_insert.html')
            self.frame_insert_view = (J2TemplateView.
                                      create_template(html, 'Frame Insert'))

            self.banner_html = config.get('banner_html', 'banner.html')

            if config.get('enable_memento', False):
                self.response_class = MementoResponse

        else:
            self.frame_insert_view = None
            self.banner_html = None

    def render_search_page(self, wbrequest, **kwargs):
        return self.search_view.render_response(wbrequest=wbrequest,
                                                prefix=wbrequest.wb_prefix,
                                                **kwargs)

    def __call__(self, wbrequest):
        # root search page
        if wbrequest.wb_url_str == '/':
            return self.render_search_page(wbrequest)

        # render top level frame if in frame mode
        # (not supported in proxy mode)
        if (self.is_frame_mode and wbrequest.wb_url and
             not wbrequest.wb_url.is_query() and
             not wbrequest.options['is_proxy']):

            if wbrequest.wb_url.is_top_frame:
                return self.get_top_frame_response(wbrequest)
            else:
                wbrequest.final_mod = 'tf_'

        try:
            return self.handle_request(wbrequest)
        except NotFoundException as nfe:
            return self.handle_not_found(wbrequest, nfe)

    def get_top_frame_params(self, wbrequest, mod=''):
        embed_url = wbrequest.wb_url.to_str(mod=mod)

        if wbrequest.wb_url.timestamp:
            timestamp = wbrequest.wb_url.timestamp
        else:
            timestamp = datetime_to_timestamp(datetime.utcnow())

        params = dict(embed_url=embed_url,
                      wbrequest=wbrequest,
                      timestamp=timestamp,
                      url=wbrequest.wb_url.get_url(),
                      banner_html=self.banner_html)

        return params

    def get_top_frame_response(self, wbrequest):
        params = self.get_top_frame_params(wbrequest)

        headers = [('Content-Type', 'text/html; charset=utf-8')]
        status_headers = StatusAndHeaders('200 OK', headers)

        template_result = self.frame_insert_view.render_to_string(**params)
        body = template_result.encode('utf-8')

        return self.response_class(status_headers, [body], wbrequest=wbrequest)


#=================================================================
# Standard WB Handler
#=================================================================
class WBHandler(SearchPageWbUrlHandler):
    def __init__(self, query_handler, config=None):
        super(WBHandler, self).__init__(config)

        self.index_reader = query_handler
        self.not_found_view = (J2TemplateView.
                               create_template(config.get('not_found_html'),
                               'Not Found Error'))

        self.replay = self._init_replay_view(config)

        self.fallback_handler = None
        self.fallback_name = config.get('fallback')

    def _init_replay_view(self, config):
        cookie_maker = config.get('cookie_maker')
        record_loader = ArcWarcRecordLoader(cookie_maker=cookie_maker)

        paths = config.get('archive_paths')

        resolving_loader = ResolvingLoader(paths=paths,
                                           record_loader=record_loader)

        return ReplayView(resolving_loader, config)

    def resolve_refs(self, handler_dict):
        if self.fallback_name:
            self.fallback_handler = handler_dict.get(self.fallback_name)

    def handle_request(self, wbrequest):
        cdx_lines, output = self.index_reader.load_for_request(wbrequest)

        if output != 'text' and wbrequest.wb_url.is_replay():
            return self.handle_replay(wbrequest, cdx_lines)
        else:
            return self.handle_query(wbrequest, cdx_lines, output)

    def handle_query(self, wbrequest, cdx_lines, output):
        return self.index_reader.make_cdx_response(wbrequest,
                                                   cdx_lines,
                                                   output)

    def handle_replay(self, wbrequest, cdx_lines):
        cdx_callback = self.index_reader.cdx_load_callback(wbrequest)

        return self.replay.render_content(wbrequest,
                                          cdx_lines,
                                          cdx_callback)

    def handle_not_found(self, wbrequest, nfe):
        # check fallback: only for replay queries and not for identity
        if (self.fallback_handler and
            not wbrequest.wb_url.is_query() and
            not wbrequest.wb_url.is_identity):
            return self.fallback_handler(wbrequest)

        # if capture query, just return capture page
        if wbrequest.wb_url.is_query():
            return self.index_reader.make_cdx_response(wbrequest, [], 'html')
        else:
            return self.not_found_view.render_response(status='404 Not Found',
                                                       env=wbrequest.env,
                                                       url=wbrequest.wb_url.url)


#=================================================================
# Static Content Handler
#=================================================================
class StaticHandler(BaseHandler):
    def __init__(self, static_path):
        mimetypes.init()

        self.static_path = static_path
        self.block_loader = BlockLoader()

    def __call__(self, wbrequest):
        url = wbrequest.wb_url_str.split('?')[0]
        full_path = self.static_path + url

        try:
            data = self.block_loader.load(full_path)

            try:
                data.seek(0, 2)
                size = data.tell()
                data.seek(0)
                headers = [('Content-Length', str(size))]
            except IOError:
                headers = None

            if 'wsgi.file_wrapper' in wbrequest.env:
                reader = wbrequest.env['wsgi.file_wrapper'](data)
            else:
                reader = iter(lambda: data.read(), '')

            content_type = 'application/octet-stream'

            guessed = mimetypes.guess_type(full_path)
            if guessed[0]:
                content_type = guessed[0]

            return WbResponse.text_stream(reader,
                                          content_type=content_type,
                                          headers=headers)

        except IOError:
            raise NotFoundException('Static File Not Found: ' +
                                    wbrequest.wb_url_str)


#=================================================================
# Debug Handlers
#=================================================================
class DebugEchoEnvHandler(BaseHandler):  # pragma: no cover
    def __call__(self, wbrequest):
        return WbResponse.text_response(str(wbrequest.env))


#=================================================================
class DebugEchoHandler(BaseHandler):  # pragma: no cover
    def __call__(self, wbrequest):
        return WbResponse.text_response(str(wbrequest))
