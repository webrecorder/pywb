from pywb.framework.basehandlers import WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.archivalrouter import ArchivalRouter, Route

from pywb.rewrite.rewrite_live import LiveRewriter
from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import HttpsUrlRewriter

from handlers import StaticHandler, SearchPageWbUrlHandler
from views import HeadInsertView

from pywb.utils.wbexception import WbException

import json
import requests
import hashlib

from rangecache import range_cache


#=================================================================
class LiveResourceException(WbException):
    def status(self):
        return '400 Bad Live Resource'


#=================================================================
class RewriteHandler(SearchPageWbUrlHandler):

    LIVE_COOKIE = 'pywb.timestamp={0}; max-age=60'

    youtubedl = None

    def __init__(self, config):
        super(RewriteHandler, self).__init__(config)

        self.default_proxy = config.get('proxyhostport')
        self.rewriter = LiveRewriter(is_framed_replay=self.is_frame_mode,
                                     default_proxy=self.default_proxy)

        self.head_insert_view = HeadInsertView.init_from_config(config)

        self.live_cookie = config.get('live-cookie', self.LIVE_COOKIE)

        self.ydl = None

    def handle_request(self, wbrequest):
        try:
            return self.render_content(wbrequest)

        except Exception as exc:
            import traceback
            err_details = traceback.format_exc(exc)
            print err_details

            url = wbrequest.wb_url.url
            msg = 'Could not load the url from the live web: ' + url
            raise LiveResourceException(msg=msg, url=url)

    def _live_request_headers(self, wbrequest):
        return {}

    def render_content(self, wbrequest):
        if wbrequest.wb_url.mod == 'vi_':
            return self.get_video_info(wbrequest)

        head_insert_func = self.head_insert_view.create_insert_func(wbrequest)
        req_headers = self._live_request_headers(wbrequest)

        ref_wburl_str = wbrequest.extract_referrer_wburl_str()
        if ref_wburl_str:
            wbrequest.env['REL_REFERER'] = WbUrl(ref_wburl_str).url

        proxies = None  # default
        ping_url = None
        ping_cache_key = None
        ping_range_header = None

        if self.default_proxy and range_cache:
            rangeres = range_cache.is_ranged(wbrequest)
            if rangeres:
                url, start, end, use_206 = rangeres
                proxies = False

                # force a bound on unbounded range
                if use_206 and wbrequest.env['HTTP_RANGE'].endswith('-'):
                    range_h = 'bytes={0}-{1}'.format(start, end)
                    wbrequest.env['HTTP_RANGE'] = range_h
                    print('BOUNDING: ' + range_h)

                hash_ = hashlib.md5()
                hash_.update(url)
                ping_cache_key = hash_.hexdigest()

                if ping_cache_key not in range_cache.cache:
                    ping_url = url


        result = self.rewriter.fetch_request(wbrequest.wb_url.url,
                                             wbrequest.urlrewriter,
                                             head_insert_func=head_insert_func,
                                             req_headers=req_headers,
                                             env=wbrequest.env,
                                             proxies=proxies)

        wbresponse = self._make_response(wbrequest, *result)

        if ping_url:
            self._proxy_ping(wbrequest, wbresponse,
                             ping_url, ping_cache_key)

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

    def _proxy_ping(self, wbrequest, wbresponse, url, key):
        def do_proxy_ping():
            proxies = {'http': self.default_proxy,
                       'https': self.default_proxy}

            headers = self._live_request_headers(wbrequest)
            headers['Connection'] = 'close'

            if key in range_cache.cache:
                return

            try:
                # mark as pinged
                range_cache.cache[key] = '1'

                resp = requests.get(url=url,
                                    headers=headers,
                                    proxies=proxies,
                                    verify=False,
                                    stream=True)

                # don't actually read whole response, proxy response for writing it
                resp.close()
            except:
                del range_cache.cache[key]

        def check_buff_gen(gen):
            for x in gen:
                yield x

            do_proxy_ping()

        wbresponse.body = check_buff_gen(wbresponse.body)
        return wbresponse

    def get_video_info(self, wbrequest):
        if not self.youtubedl:
            self.youtubedl = YoutubeDLWrapper()

        info = self.youtubedl.extract_info(wbrequest.wb_url.url)

        content_type = 'application/vnd.youtube-dl_formats+json'
        metadata = json.dumps(info)

        if self.default_proxy:
            proxies = {'http': self.default_proxy}

            headers = self._live_request_headers(wbrequest)
            headers['Content-Type'] = content_type

            url = HttpsUrlRewriter.remove_https(wbrequest.wb_url.url)

            response = requests.request(method='PUTMETA',
                                        url=url,
                                        data=metadata,
                                        headers=headers,
                                        proxies=proxies,
                                        verify=False)

        return WbResponse.text_response(metadata, content_type=content_type)

    def __str__(self):
        return 'Live Web Rewrite Handler'


#=================================================================
class YoutubeDLWrapper(object):
    """ Used to wrap youtubedl import, since youtubedl currently overrides
    global HTMLParser.locatestarttagend regex with a different regex
    that doesn't quite work.

    This wrapper ensures that this regex is only set for YoutubeDL and unset
    otherwise
    """
    def __init__(self):
        import HTMLParser as htmlparser
        self.htmlparser = htmlparser

        self.orig_tagregex = htmlparser.locatestarttagend

        from youtube_dl import YoutubeDL as YoutubeDL

        self.ydl_tagregex = htmlparser.locatestarttagend

        htmlparser.locatestarttagend = self.orig_tagregex

        self.ydl = YoutubeDL(dict(simulate=True,
                                  youtube_include_dash_manifest=False))
        self.ydl.add_default_info_extractors()

    def extract_info(self, url):
        info = None
        try:
            self.htmlparser.locatestarttagend = self.ydl_tagregex
            info = self.ydl.extract_info(url)
        finally:
            self.htmlparser.locatestarttagend = self.orig_tagregex

        return info


#=================================================================
def create_live_rewriter_app(config={}):
    routes = [Route('rewrite', RewriteHandler(config)),
              Route('static/default', StaticHandler('pywb/static/'))
             ]

    return ArchivalRouter(routes, hostpaths=['http://localhost:8080'])
