import pkgutil
import mimetypes
import time
import logging

from datetime import datetime

from pywb.utils.wbexception import NotFoundException
from pywb.utils.loaders import LocalFileLoader
from pywb.utils.statusandheaders import StatusAndHeaders

from pywb.framework.basehandlers import BaseHandler, WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse

from pywb.warc.recordloader import ArcWarcRecordLoader
from pywb.warc.resolvingloader import ResolvingLoader
from pywb.warc.pathresolvers import PathResolverMapper

from pywb.webapp.views import J2TemplateView, init_view
from pywb.webapp.replay_views import ReplayView
from pywb.framework.memento import MementoResponse
from pywb.utils.timeutils import datetime_to_timestamp


#=================================================================
class SearchPageWbUrlHandler(WbUrlHandler):
    """
    Loads a default search page html template to be shown when
    the wb_url is empty
    """
    def __init__(self, config):
        self.search_view = init_view(config, 'search_html')

        self.is_frame_mode = config.get('framed_replay', False)
        self.frame_mod = 'tf_'
        self.replay_mod = ''

        self.response_class = WbResponse

        if self.is_frame_mode:
            #html = config.get('frame_insert_html', 'templates/frame_insert.html')
            #self.search_view = J2TemplateView(html, config.get('jinja_env'))
            self.frame_insert_view = init_view(config, 'frame_insert_html')
            assert(self.frame_insert_view)

            self.banner_html = config.get('banner_html', 'banner.html')

            if config.get('enable_memento', False):
                self.response_class = MementoResponse

            if self.is_frame_mode == 'inverse':
                self.frame_mod = ''
                self.replay_mod = 'mp_'

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

        wbrequest.options['replay_mod'] = self.replay_mod
        wbrequest.options['frame_mod'] = self.frame_mod

        # render top level frame if in frame mode
        # (not supported in proxy mode)
        if (self.is_frame_mode and wbrequest.wb_url and
             not wbrequest.wb_url.is_query() and
             not wbrequest.options['is_proxy']):

            if wbrequest.wb_url.mod == self.frame_mod:
                wbrequest.options['is_top_frame'] = True
                return self.get_top_frame_response(wbrequest)
            else:
                wbrequest.options['is_framed'] = True
                wbrequest.final_mod = self.frame_mod
        else:
            wbrequest.options['is_framed'] = False

        try:
            return self.handle_request(wbrequest)
        except NotFoundException as nfe:
            return self.handle_not_found(wbrequest, nfe)

    def get_top_frame_params(self, wbrequest, mod):
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
        params = self.get_top_frame_params(wbrequest, mod=self.replay_mod)

        headers = [('Content-Type', 'text/html')]
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
        self.not_found_view = init_view(config, 'not_found_html')

        self.replay = self._init_replay_view(config)

        self.fallback_handler = None
        self.fallback_name = config.get('fallback')

    def _init_replay_view(self, config):
        cookie_maker = config.get('cookie_maker')
        record_loader = ArcWarcRecordLoader(cookie_maker=cookie_maker)

        paths = config.get('archive_paths')

        resolving_loader = ResolvingLoader(PathResolverMapper()(paths),
                                           record_loader=record_loader)

        return ReplayView(resolving_loader, config)

    def resolve_refs(self, handler_dict):
        if self.fallback_name:
            self.fallback_handler = handler_dict.get(self.fallback_name)
            logging.debug('Fallback Handler: ' + self.fallback_name)

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
            output = self.index_reader.get_output_type(wbrequest.wb_url)
            return self.index_reader.make_cdx_response(wbrequest, iter([]), output)
        else:
            return self.not_found_view.render_response(status='404 Not Found',
                                                       wbrequest=wbrequest,
                                                       url=wbrequest.wb_url.url)


#=================================================================
# Static Content Handler
#=================================================================
class StaticHandler(BaseHandler):
    def __init__(self, static_path):
        mimetypes.init()

        self.static_path = static_path
        self.block_loader = LocalFileLoader()

    def __call__(self, wbrequest):
        url = wbrequest.wb_url_str.split('?')[0]
        full_path = self.static_path + url

        try:
            data = self.block_loader.load(full_path)

            data.seek(0, 2)
            size = data.tell()
            data.seek(0)
            headers = [('Content-Length', str(size))]

            reader = None

            if 'wsgi.file_wrapper' in wbrequest.env:
                try:
                    reader = wbrequest.env['wsgi.file_wrapper'](data)
                except:
                    pass

            if not reader:
                reader = iter(lambda: data.read(), b'')

            content_type = 'application/octet-stream'

            guessed = mimetypes.guess_type(full_path)
            if guessed[0]:
                content_type = guessed[0]

            return WbResponse.bin_stream(reader,
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
