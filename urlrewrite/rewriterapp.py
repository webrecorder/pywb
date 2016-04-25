import requests

from pywb.rewrite.rewrite_content import RewriteContent
from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import UrlRewriter

from pywb.utils.wbexception import WbException
from pywb.utils.canonicalize import canonicalize
from pywb.utils.timeutils import http_date_to_timestamp
from pywb.utils.loaders import extract_client_cookie

from pywb.cdx.cdxobject import CDXObject
from pywb.warc.recordloader import ArcWarcRecordLoader
from pywb.framework.wbrequestresponse import WbResponse


from urlrewrite.rewriteinputreq import RewriteInputRequest
from urlrewrite.templateview import JinjaEnv, HeadInsertView, TopFrameView, BaseInsertView

from io import BytesIO
import gevent
import json


# ============================================================================
class UpstreamException(WbException):
    def __init__(self, status_code, url, details):
        super(UpstreamException, self).__init__(url=url, msg=details)
        self.status_code = status_code


# ============================================================================
class RewriterApp(object):
    def __init__(self, framed_replay=False, jinja_env=None, config=None):
        self.loader = ArcWarcRecordLoader()

        config = config or {}

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
        self.error_view = BaseInsertView(self.jinja_env, 'error.html')
        self.query_view = BaseInsertView(self.jinja_env, config.get('query_html', 'query.html'))

    def call_with_params(self, **kwargs):
        def run_app(environ, start_response):
            environ['pywb.kwargs'] = kwargs
            return self(environ, start_response)

        return run_app

    def __call__(self, environ, start_response):
        wb_url = self.get_wburl(environ)
        kwargs = environ.get('pywb.kwargs', {})

        try:
            response = self.render_content(wb_url, kwargs, environ)
        except UpstreamException as ue:
            response = self.handle_error(environ, ue)

        return response(environ, start_response)

    def render_content(self, wb_url, kwargs, environ):
        wb_url = WbUrl(wb_url)
        #if wb_url.mod == 'vi_':
        #    return self._get_video_info(wbrequest)

        host_prefix = self.get_host_prefix(environ)
        rel_prefix = self.get_rel_prefix(environ)
        full_prefix = host_prefix + rel_prefix

        resp = self.handle_custom_response(environ, wb_url,
                                           full_prefix, host_prefix, kwargs)
        if resp is not None:
            return WbResponse.text_response(resp, content_type='text/html')

        urlrewriter = UrlRewriter(wb_url,
                                  prefix=full_prefix,
                                  full_prefix=full_prefix,
                                  rel_prefix=rel_prefix)

        self.unrewrite_referrer(environ)

        url = wb_url.url
        urlkey = canonicalize(url)

        inputreq = RewriteInputRequest(environ, urlkey, url,
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

                    del environ['HTTP_RANGE']
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

            details = dict(args=kwargs, error=error)
            raise UpstreamException(r.status_code, url=url, details=details)

        if async_record_url:
            #print('ASYNC REC', async_record_url)
            environ.pop('HTTP_RANGE', '')
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

        if self.is_ajax(environ):
            head_insert_func = None
        else:
            top_url = self.get_top_url(full_prefix, wb_url, cdx, kwargs)
            head_insert_func = (self.head_insert_view.
                                    create_insert_func(wb_url,
                                                       full_prefix,
                                                       host_prefix,
                                                       top_url,
                                                       environ,
                                                       self.framed_replay))

        result = self.content_rewriter.rewrite_content(urlrewriter,
                                               record.status_headers,
                                               record.stream,
                                               head_insert_func,
                                               urlkey,
                                               cdx)

        status_headers, gen, is_rw = result
        return WbResponse(status_headers, gen)

    def get_top_url(self, full_prefix, wb_url, cdx, kwargs):
        top_url = full_prefix
        top_url += wb_url.to_str(mod='')
        return top_url

    def _do_async_req(self, *args):
        count = 0
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
            try:
                r.raw.close()
            except:
                pass

    def handle_error(self, environ, ue):
        error_html = self.error_view.render_to_string(environ,
                                                      err_msg=ue.url,
                                                      err_details=ue.msg)

        return WbResponse.text_response(error_html, content_type='text/html')

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

        upstream_url += '&output=json'
        upstream_url += '&from=' + wb_url.timestamp + '&to=' + wb_url.end_timestamp

        r = requests.get(upstream_url)

        return r.text

    def handle_query(self, environ, wb_url, kwargs):
        res = self.do_query(wb_url, kwargs)

        def format_cdx(text):
            cdx_lines = text.rstrip().split('\n')
            for cdx in cdx_lines:
                if not cdx:
                    continue

                cdx = json.loads(cdx)
                self.process_query_cdx(cdx, wb_url, kwargs)
                yield cdx

        prefix = self.get_full_prefix(environ)

        params = dict(url=wb_url.url,
                      prefix=prefix,
                      cdx_lines=list(format_cdx(res)))

        extra_params = self.get_query_params(wb_url, kwargs)
        if extra_params:
            params.update(extra_params)

        return self.query_view.render_to_string(environ, **params)

    def process_query_cdx(self, cdx, wb_url, kwargs):
        return

    def get_query_params(self, wb_url, kwargs):
        return None

    def get_host_prefix(self, environ):
        #return request.urlparts.scheme + '://' + request.urlparts.netloc
        url = environ['wsgi.url_scheme'] + '://'
        if environ.get('HTTP_HOST'):
            url += environ['HTTP_HOST']
        else:
            url += environ['SERVER_NAME']
            if environ['wsgi.url_scheme'] == 'https':
                if environ['SERVER_PORT'] != '443':
                   url += ':' + environ['SERVER_PORT']
            else:
                if environ['SERVER_PORT'] != '80':
                   url += ':' + environ['SERVER_PORT']

        return url

    def get_rel_prefix(self, environ):
        #return request.script_name
        return environ.get('SCRIPT_NAME') + '/'

    def get_full_prefix(self, environ):
        return self.get_host_prefix(environ) + self.get_rel_prefix(environ)

    def get_wburl(self, environ):
        wb_url = environ.get('PATH_INFO', '/')[1:]
        if environ.get('QUERY_STRING'):
            wb_url += '?' + environ.get('QUERY_STRING')

        return wb_url

    def unrewrite_referrer(self, environ):
        referrer = environ.get('HTTP_REFERER')
        if not referrer:
            return False

        full_prefix = self.get_full_prefix(environ)

        if referrer.startswith(full_prefix):
            referrer = referrer[len(full_prefix):]
            environ['HTTP_REFERER'] = WbUrl(referrer).url
            return True

        return False

    def is_ajax(self, environ):
        value = environ.get('HTTP_X_REQUESTED_WITH')
        value = value or environ.get('HTTP_X_PYWB_REQUESTED_WITH')
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

    def handle_custom_response(self, environ, wb_url, full_prefix, host_prefix, kwargs):
        if wb_url.is_query():
            return self.handle_query(environ, wb_url, kwargs)
            #return self.do_query(wb_url, kwargs)

        if self.framed_replay and wb_url.mod == self.frame_mod:
            extra_params = self.get_top_frame_params(wb_url, kwargs)
            return self.frame_insert_view.get_top_frame(wb_url,
                                                        full_prefix,
                                                        host_prefix,
                                                        environ,
                                                        self.frame_mod,
                                                        self.replay_mod,
                                                        coll='',
                                                        extra_params=extra_params)

        return None
