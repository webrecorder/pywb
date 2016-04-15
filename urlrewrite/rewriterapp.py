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

from urlrewrite.rewriteinputreq import RewriteInputRequest
from urlrewrite.templateview import JinjaEnv, HeadInsertView, TopFrameView

from io import BytesIO
import gevent


# ============================================================================
class RewriterApp(object):
    def __init__(self, framed_replay=False, jinja_env=None):
        self.loader = ArcWarcRecordLoader()

        self.framed_replay = framed_replay
        self.frame_mod = ''
        self.replay_mod = 'mp_'

        frame_type = 'inverse' if framed_replay else False

        self.content_rewriter = RewriteContent(is_framed_replay=frame_type)

        if not jinja_env:
            jinja_env = JinjaEnv(globals={'static_path': 'static/__pywb'})

        self.jinja_env = jinja_env
        self.head_insert_view = HeadInsertView(self.jinja_env, 'head_insert.html', 'banner.html')
        self.frame_insert_view = TopFrameView(self.jinja_env, 'frame_insert.html', 'banner.html')

    def render_content(self, wb_url, **kwargs):
        wb_url = WbUrl(wb_url)
        #if wb_url.mod == 'vi_':
        #    return self._get_video_info(wbrequest)

        host_prefix = self.get_host_prefix()
        rel_prefix = self.get_rel_prefix()
        full_prefix = host_prefix + rel_prefix

        resp = self.handle_custom_response(wb_url, full_prefix, host_prefix, kwargs)
        if resp is not None:
            return resp

        urlrewriter = UrlRewriter(wb_url,
                                  prefix=full_prefix,
                                  full_prefix=full_prefix,
                                  rel_prefix=rel_prefix)

        self.unrewrite_referrer()

        url = wb_url.url
        urlkey = canonicalize(url)

        inputreq = RewriteInputRequest(request.environ, urlkey, url,
                                       self.content_rewriter)

        mod_url = None
        use_206 = False
        rangeres = None

        readd_range = False
        async_record_url = None

        if kwargs.get('type') == 'record':
            rangeres = inputreq.extract_range()

            if rangeres:
                mod_url, start, end, use_206 = rangeres

                # if bytes=0- Range request,
                # simply remove the range and still proxy
                if start == 0 and not end and use_206:
                    url = mod_url
                    wb_url.url = mod_url
                    inputreq.url = mod_url

                    del request.environ['HTTP_RANGE']
                    readd_range = True
                else:
                    async_record_url = mod_url

        r = self._do_req(inputreq, url, wb_url, kwargs,
                         async_record_url is not None)

        if r.status_code >= 400:
            error = None
            try:
                error = r.raw.read()
                r.raw.close()
            except:
                pass

            if error:
                error = error.decode('utf-8')
            else:
                error = ''

            data = dict(url=url, args=kwargs, error=error)
            raise HTTPError(r.status_code, exception=data)

        if async_record_url:
            #print('ASYNC REC', async_record_url)
            request.environ.pop('HTTP_RANGE', '')
            gevent.spawn(self._do_async_req,
                         inputreq,
                         async_record_url,
                         wb_url,
                         kwargs,
                         False)

        record = self.loader.parse_record_stream(r.raw)

        cdx = CDXObject()
        cdx['urlkey'] = urlkey
        cdx['timestamp'] = http_date_to_timestamp(r.headers.get('Memento-Datetime'))
        cdx['url'] = url

        self._add_custom_params(cdx, r.headers, kwargs)

        if readd_range:
            content_length = (record.status_headers.
                              get_header('Content-Length'))
            try:
                content_length = int(content_length)
                record.status_headers.add_range(0, content_length,
                                                   content_length)
            except (ValueError, TypeError):
                pass

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
            response.add_header(n, v)

        return gen

    def _do_async_req(self, *args):
        count = 0
        #print('ASYNC')
        try:
            r = self._do_req(*args)
            while True:
                buff = r.raw.read(8192)
                count += len(buff)
                if not buff:
                    return
        except:
            import traceback
            traceback.print_exc()

        finally:
            #print('CLOSING')
            #print('READ ASYNC', count)
            try:
                r.raw.close()
            except:
                pass


    def _do_req(self, inputreq, url, wb_url, kwargs, skip):
        req_data = inputreq.reconstruct_request(url)

        headers = {'Content-Length': len(req_data),
                   'Content-Type': 'application/request'}

        if skip:
            headers['Recorder-Skip'] = '1'

        if wb_url.is_latest_replay():
            closest = 'now'
        else:
            closest = wb_url.timestamp

        upstream_url = self.get_upstream_url(url, wb_url, closest, kwargs)
        r = requests.post(upstream_url,
                          data=BytesIO(req_data),
                          headers=headers,
                          stream=True)

        return r

    def do_query(self, wb_url, kwargs):
        upstream_url = self.get_upstream_url(wb_url.url, wb_url, 'now', kwargs)
        upstream_url = upstream_url.replace('/resource/postreq', '/index')
        r = requests.get(upstream_url + '&output=json')
        print(r.text)
        return r.text

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
            request.environ['HTTP_REFERER'] = WbUrl(referrer).url
            return True

        return False

    def is_ajax(self):
        value = request.environ.get('HTTP_X_REQUESTED_WITH')
        value = value or request.environ.get('HTTP_X_PYWB_REQUESTED_WITH')
        if value and value.lower() == 'xmlhttprequest':
            return True

        return False

    def get_upstream_url(self, url, wb_url, closest, kwargs):
        raise NotImplemented()

    def _add_custom_params(self, cdx, headers, kwargs):
        cdx['is_live'] = 'true'
        pass

    def get_top_frame_params(self, wb_url, kwargs):
        return None

    def handle_custom_response(self, wb_url, full_prefix, host_prefix, kwargs):
        if wb_url.is_query():
            return self.do_query(wb_url, kwargs)

        if self.framed_replay and wb_url.mod == self.frame_mod:
            extra_params = self.get_top_frame_params(wb_url, kwargs)
            return self.frame_insert_view.get_top_frame(wb_url,
                                                        full_prefix,
                                                        host_prefix,
                                                        request.environ,
                                                        self.frame_mod,
                                                        self.replay_mod,
                                                        coll='',
                                                        extra_params=extra_params)

        return None
