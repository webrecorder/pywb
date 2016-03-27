import requests

from bottle import request, response, HTTPError

from pywb.rewrite.rewrite_content import RewriteContent
from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import UrlRewriter

from pywb.utils.canonicalize import canonicalize
from pywb.utils.timeutils import http_date_to_timestamp
from pywb.utils.loaders import extract_client_cookie

from pywb.cdx.cdxobject import CDXObject
from pywb.warc.recordloader import ArcWarcRecordLoader

from rewriteinputreq import RewriteInputRequest
from templateview import JinjaEnv, HeadInsertView, TopFrameView

from io import BytesIO


# ============================================================================
class RewriterApp(object):
    def __init__(self, framed_replay=False):
        self.loader = ArcWarcRecordLoader()

        self.framed_replay = framed_replay
        self.frame_mod = ''
        self.replay_mod = 'mp_'

        frame_type = 'inverse' if framed_replay else False

        self.content_rewriter = RewriteContent(is_framed_replay=frame_type)

        self.jenv = JinjaEnv(globals={'static_path': 'static/__pywb'})
        self.head_insert_view = HeadInsertView(self.jenv, 'head_insert.html', 'banner.html')
        self.frame_insert_view = TopFrameView(self.jenv, 'frame_insert.html', 'banner.html')

    def render_content(self, wb_url, **kwargs):
        wb_url = WbUrl(wb_url)
        #if wb_url.mod == 'vi_':
        #    return self._get_video_info(wbrequest)

        host_prefix = self.get_host_prefix()
        rel_prefix = self.get_rel_prefix()
        full_prefix = host_prefix + rel_prefix

        if self.framed_replay and wb_url.mod == self.frame_mod:
            return self.frame_insert_view.get_top_frame(wb_url,
                                                        full_prefix,
                                                        host_prefix,
                                                        self.frame_mod,
                                                        self.replay_mod)

        urlrewriter = UrlRewriter(wb_url,
                                  prefix=full_prefix,
                                  full_prefix=full_prefix,
                                  rel_prefix=rel_prefix)

        self.unrewrite_referrer()

        url = wb_url.url
        urlkey = canonicalize(url)

        inputreq = RewriteInputRequest(request.environ, urlkey, url,
                                       self.content_rewriter)

        req_data = inputreq.reconstruct_request(url)

        headers = {'Content-Length': len(req_data),
                   'Content-Type': 'application/request'}

        if wb_url.is_latest_replay():
            closest = 'now'
        else:
            closest = wb_url.timestamp

        upstream_url = self.get_upstream_url(url, closest, kwargs)

        r = requests.post(upstream_url,
                          data=BytesIO(req_data),
                          headers=headers,
                          stream=True)

        if r.status_code >= 400:
            try:
                r.raw.close()
            except:
                pass

            data = dict(url=url, args=kwargs)
            raise HTTPError(r.status_code, exception=data)

        record = self.loader.parse_record_stream(r.raw)

        cdx = CDXObject()
        cdx['urlkey'] = urlkey
        cdx['timestamp'] = http_date_to_timestamp(r.headers.get('Memento-Datetime'))
        cdx['url'] = url

        self._add_custom_params(cdx, kwargs)

        if self.is_ajax():
            head_insert_func = None
        else:
            head_insert_func = (self.head_insert_view.
                                    create_insert_func(wb_url,
                                                       full_prefix,
                                                       host_prefix,
                                                       request.environ,
                                                       self.framed_replay))

        result = self.content_rewriter.rewrite_content(urlrewriter,
                                               record.status_headers,
                                               record.stream,
                                               head_insert_func,
                                               urlkey,
                                               cdx)

        status_headers, gen, is_rw = result

        response.status = int(status_headers.get_statuscode())

        for n, v in status_headers.headers:
            response.headers[n] = v

        return gen

    def get_host_prefix(self):
        return request.urlparts.scheme + '://' + request.urlparts.netloc

    def get_rel_prefix(self):
        return request.script_name

    def get_full_prefix(self):
        return self.get_host_prefix() + self.get_rel_prefix()

    def unrewrite_referrer(self):
        referrer = request.environ.get('HTTP_REFERER')
        if not referrer:
            return False

        full_prefix = self.get_full_prefix()

        if referrer.startswith(full_prefix):
            referrer = referrer[len(full_prefix):]
            request.environ['HTTP_REFERER'] = referrer
            return True

        return False

    def is_ajax(self):
        value = request.environ.get('HTTP_X_REQUESTED_WITH')
        if value and value.lower() == 'xmlhttprequest':
            return True

        return False

    def get_upstream_url(self, url, closest, kwargs):
        raise NotImplemented()

    def _add_custom_params(self, cdx, kwargs):
        pass
