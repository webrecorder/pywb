from pywb.framework.basehandlers import WbUrlHandler
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.archivalrouter import ArchivalRouter, Route
from pywb.framework.cache import create_cache

from pywb.rewrite.rewrite_live import LiveRewriter
from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import HttpsUrlRewriter

from handlers import StaticHandler, SearchPageWbUrlHandler
from views import HeadInsertView

from pywb.utils.wbexception import WbException

import json
import requests
import hashlib


#=================================================================
class LiveResourceException(WbException):
    def status(self):
        return '400 Bad Live Resource'


#=================================================================
class RewriteHandler(SearchPageWbUrlHandler):

    LIVE_COOKIE = 'pywb.timestamp={0}; max-age=60'

    YT_DL_TYPE = 'application/vnd.youtube-dl_formats+json'

    youtubedl = None

    def __init__(self, config):
        super(RewriteHandler, self).__init__(config)

        proxyhostport = config.get('proxyhostport')
        self.rewriter = LiveRewriter(is_framed_replay=self.is_frame_mode,
                                     proxies=proxyhostport)

        self.proxies = self.rewriter.proxies

        self.head_insert_view = HeadInsertView.init_from_config(config)

        self.live_cookie = config.get('live-cookie', self.LIVE_COOKIE)

        self.verify = config.get('verify_ssl', True)

        self.ydl = None

        self._cache = None

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
            return self._get_video_info(wbrequest)

        head_insert_func = self.head_insert_view.create_insert_func(wbrequest)
        req_headers = self._live_request_headers(wbrequest)

        ref_wburl_str = wbrequest.extract_referrer_wburl_str()
        if ref_wburl_str:
            wbrequest.env['REL_REFERER'] = WbUrl(ref_wburl_str).url

        ignore_proxies = False
        use_206 = False
        url = None
        rangeres = None

        readd_range = False
        cache_key = None

        if self.proxies:
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
                    ignore_proxies = True

                    # sets cache_key only if not already cached
                    cache_key = self._get_cache_key('r:', url)

        result = self.rewriter.fetch_request(wbrequest.wb_url.url,
                                             wbrequest.urlrewriter,
                                             head_insert_func=head_insert_func,
                                             req_headers=req_headers,
                                             env=wbrequest.env,
                                             ignore_proxies=ignore_proxies,
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

        if cache_key:
            self._add_proxy_ping(cache_key, url, wbrequest, wbresponse)

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
        hash_.update(url)
        key = hash_.hexdigest()
        key = prefix + key
        return key

    def _add_proxy_ping(self, key, url, wbrequest, wbresponse):
        def do_ping():
            headers = self._live_request_headers(wbrequest)
            headers['Connection'] = 'close'

            try:
                # mark as pinged
                self._cache[key] = '1'

                resp = requests.get(url=url,
                                    headers=headers,
                                    proxies=self.proxies,
                                    verify=False,
                                    stream=True)

                # don't actually read whole response,
                # proxy response for writing it
                resp.close()
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
        if not self.youtubedl:
            self.youtubedl = YoutubeDLWrapper()

        if not video_url:
            video_url = wbrequest.wb_url.url

        if not info_url:
            info_url = wbrequest.wb_url.url

        cache_key = None
        if self.proxies:
            cache_key = self._get_cache_key('v:', video_url)

        info = self.youtubedl.extract_info(video_url)

        #if info and info.formats and len(info.formats) == 1:

        content_type = self.YT_DL_TYPE
        metadata = json.dumps(info)

        if (self.proxies and cache_key):
            headers = self._live_request_headers(wbrequest)
            headers['Content-Type'] = content_type

            info_url = HttpsUrlRewriter.remove_https(info_url)

            response = requests.request(method='PUTMETA',
                                        url=info_url,
                                        data=metadata,
                                        headers=headers,
                                        proxies=self.proxies,
                                        verify=False)

            self._cache[cache_key] = '1'

        return WbResponse.text_response(metadata, content_type=content_type)


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
              Route('static/__pywb', StaticHandler('pywb/static/'))
             ]

    return ArchivalRouter(routes, hostpaths=['http://localhost:8080'])
