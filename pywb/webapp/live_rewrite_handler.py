from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.cache import create_cache

from pywb.rewrite.rewrite_live import LiveRewriter
from pywb.rewrite.wburl import WbUrl

from pywb.webapp.handlers import StaticHandler, SearchPageWbUrlHandler
from pywb.webapp.views import HeadInsertView

from pywb.utils.wbexception import LiveResourceException

import json
import hashlib


#=================================================================
class RewriteHandler(SearchPageWbUrlHandler):

    LIVE_COOKIE = 'pywb.timestamp={0}; max-age=60'

    YT_DL_TYPE = 'application/vnd.youtube-dl_formats+json'

    def __init__(self, config):
        super(RewriteHandler, self).__init__(config)

        proxyhostport = config.get('proxyhostport')

        live_rewriter_cls = config.get('live_rewriter_cls', LiveRewriter)

        self.live_fetcher = live_rewriter_cls(is_framed_replay=self.is_frame_mode,
                                              proxies=proxyhostport)

        self.recording = self.live_fetcher.is_recording()

        self.head_insert_view = HeadInsertView.init_from_config(config)

        self.live_cookie = config.get('live-cookie', self.LIVE_COOKIE)

        self.verify = config.get('verify_ssl', True)

        self.ydl = None

        self._cache = None

    def handle_request(self, wbrequest):
        if wbrequest.wb_url.is_query():
            type_ = wbrequest.wb_url.LATEST_REPLAY
            url = wbrequest.urlrewriter.get_new_url(type=type_, timestamp='')
            return WbResponse.redir_response(url)

        if wbrequest.options['is_ajax']:
            wbrequest.urlrewriter.rewrite_opts['is_ajax'] = True

        try:
            return self.render_content(wbrequest)

        except Exception as exc:
            import traceback
            err_details = traceback.format_exc()
            print(err_details)

            url = wbrequest.wb_url.url
            msg = 'Could not load the url from the live web: ' + url
            raise LiveResourceException(msg=msg, url=url)

    def _live_request_headers(self, wbrequest):
        return {}

    def _skip_recording(self, wbrequest):
        return False

    def render_content(self, wbrequest):
        if wbrequest.wb_url.mod == 'vi_':
            return self._get_video_info(wbrequest)

        head_insert_func = self.head_insert_view.create_insert_func(wbrequest)
        req_headers = self._live_request_headers(wbrequest)

        ref_wburl_str = wbrequest.extract_referrer_wburl_str()
        if ref_wburl_str:
            wbrequest.env['REL_REFERER'] = WbUrl(ref_wburl_str).url

        skip_recording = self._skip_recording(wbrequest)

        use_206 = False
        url = None
        rangeres = None

        readd_range = False
        cache_key = None

        if self.recording and not skip_recording:
            rangeres = wbrequest.extract_range()

            if rangeres:
                url, start, end, use_206 = rangeres

                # if bytes=0- Range request,
                # simply remove the range and still proxy
                if start == 0 and not end and use_206:
                    wbrequest.wb_url.url = url
                    del wbrequest.env['HTTP_RANGE']
                    readd_range = True
                else:
                    # disables proxy
                    skip_recording = True

                    # sets cache_key only if not already cached
                    cache_key = self._get_cache_key('r:', url)

        result = self.live_fetcher.fetch_request(wbrequest.wb_url.url,
                                             wbrequest.urlrewriter,
                                             head_insert_func=head_insert_func,
                                             req_headers=req_headers,
                                             env=wbrequest.env,
                                             skip_recording=skip_recording,
                                             verify=self.verify)

        wbresponse = self._make_response(wbrequest, *result)

        if readd_range:
            content_length = (wbresponse.status_headers.
                              get_header('Content-Length'))
            try:
                content_length = int(content_length)
                wbresponse.status_headers.add_range(0, content_length,
                                                    content_length)
            except (ValueError, TypeError):
                pass

        if self.recording and cache_key:
            self._add_rec_ping(cache_key, url, wbrequest, wbresponse)

        if rangeres:
            referrer = wbrequest.env.get('REL_REFERER')

            # also ping video info
            if referrer:
                try:
                    resp = self._get_video_info(wbrequest,
                                                info_url=referrer,
                                                video_url=url)
                except:
                    print('Error getting video info')

        return wbresponse

    def _make_response(self, wbrequest, status_headers, gen, is_rewritten):
        # if cookie set, pass recorded timestamp info via cookie
        # so that client side may be able to access it
        # used by framed mode to update frame banner
        if self.live_cookie:
            cdx = wbrequest.env.get('pywb.cdx')
            if cdx:
                value = self.live_cookie.format(cdx['timestamp'])
                status_headers.headers.append(('Set-Cookie', value))

        return WbResponse(status_headers, gen)

    def _get_cache_key(self, prefix, url):
        if not self._cache:
            self._cache = create_cache()

        key = self.create_cache_key(prefix, url)

        if key in self._cache:
            return None

        return key

    @staticmethod
    def create_cache_key(prefix, url):
        hash_ = hashlib.md5()
        hash_.update(url.encode('utf-8'))
        key = hash_.hexdigest()
        key = prefix + key
        return key

    def _add_rec_ping(self, key, url, wbrequest, wbresponse):
        def do_ping():
            headers = self._live_request_headers(wbrequest)
            headers['Connection'] = 'close'

            try:
                # mark as pinged
                self._cache[key] = '1'

                self.live_fetcher.fetch_async(url, headers)

            except:
                del self._cache[key]
                raise

        def wrap_buff_gen(gen):
            for x in gen:
                yield x

            try:
                do_ping()
            except:
                pass

        #do_ping()
        wbresponse.body = wrap_buff_gen(wbresponse.body)
        return wbresponse

    def _get_video_info(self, wbrequest, info_url=None, video_url=None):
        if not video_url:
            video_url = wbrequest.wb_url.url

        if not info_url:
            info_url = wbrequest.wb_url.url

        cache_key = None
        if self.recording:
            cache_key = self._get_cache_key('v:', video_url)

        info = self.live_fetcher.get_video_info(video_url)
        if info is None:  #pragma: no cover
            msg = ('youtube-dl is not installed, pip install youtube-dl to ' +
                   'enable improved video proxy')

            return WbResponse.text_response(text=msg, status='404 Not Found')

        #if info and info.formats and len(info.formats) == 1:

        content_type = self.YT_DL_TYPE
        metadata = json.dumps(info)

        if (self.recording and cache_key):
            headers = self._live_request_headers(wbrequest)
            headers['Content-Type'] = content_type

            if info_url.startswith('https://'):
                info_url = info_url.replace('https', 'http', 1)

            response = self.live_fetcher.add_metadata(info_url, headers, metadata)

            self._cache[cache_key] = '1'

        return WbResponse.text_response(metadata, content_type=content_type)
