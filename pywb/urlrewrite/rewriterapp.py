import requests

from pywb.rewrite.rewrite_amf import RewriteContentAMF
from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import UrlRewriter

from pywb.utils.wbexception import WbException
from pywb.utils.canonicalize import canonicalize
from pywb.utils.loaders import extract_client_cookie

from warcio.timeutils import http_date_to_timestamp
from warcio.bufferedreaders import BufferedReader
from warcio.recordloader import ArcWarcRecordLoader

from pywb.webagg.utils import BUFF_SIZE

from pywb.cdx.cdxobject import CDXObject
from pywb.framework.wbrequestresponse import WbResponse

from pywb.webagg.utils import MementoUtils, buffer_iter

from werkzeug.http import HTTP_STATUS_CODES
from six.moves.urllib.parse import urlencode

from pywb.urlrewrite.rewriteinputreq import RewriteInputRequest
from pywb.urlrewrite.templateview import JinjaEnv, HeadInsertView, TopFrameView, BaseInsertView


from io import BytesIO
from copy import copy

import gevent
import json


# ============================================================================
class UpstreamException(WbException):
    def __init__(self, status_code, url, details):
        super(UpstreamException, self).__init__(url=url, msg=details)
        self.status_code = status_code


# ============================================================================
class RewriterApp(object):
    VIDEO_INFO_CONTENT_TYPE = 'application/vnd.youtube-dl_formats+json'

    def __init__(self, framed_replay=False, jinja_env=None, config=None):
        self.loader = ArcWarcRecordLoader()

        config = config or {}
        self.paths = {}

        self.framed_replay = framed_replay
        self.frame_mod = ''
        self.replay_mod = 'mp_'

        frame_type = 'inverse' if framed_replay else False

        self.content_rewriter = RewriteContentAMF(is_framed_replay=frame_type)

        if not jinja_env:
            jinja_env = JinjaEnv(globals={'static_path': 'static/__pywb'})

        self.jinja_env = jinja_env

        self.head_insert_view = HeadInsertView(self.jinja_env, 'head_insert.html', 'banner.html')
        self.frame_insert_view = TopFrameView(self.jinja_env, 'frame_insert.html', 'banner.html')
        self.error_view = BaseInsertView(self.jinja_env, 'error.html')
        self.not_found_view = BaseInsertView(self.jinja_env, 'not_found.html')
        self.query_view = BaseInsertView(self.jinja_env, config.get('query_html', 'query.html'))

        self.cookie_tracker = None

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

    def is_framed_replay(self, wb_url):
        return (self.framed_replay and
                wb_url.mod == self.frame_mod and
                wb_url.is_replay())

    def render_content(self, wb_url, kwargs, environ):
        wb_url = WbUrl(wb_url)

        host_prefix = self.get_host_prefix(environ)
        rel_prefix = self.get_rel_prefix(environ)
        full_prefix = host_prefix + rel_prefix

        resp = self.handle_custom_response(environ, wb_url,
                                           full_prefix, host_prefix, kwargs)
        if resp is not None:
            content_type = 'text/html'

            # if not replay outer frame, specify utf-8 charset
            if not self.is_framed_replay(wb_url):
                content_type += '; charset=utf-8'

            return WbResponse.text_response(resp, content_type=content_type)

        urlrewriter = UrlRewriter(wb_url,
                                  prefix=full_prefix,
                                  full_prefix=full_prefix,
                                  rel_prefix=rel_prefix)

        self.unrewrite_referrer(environ)

        urlkey = canonicalize(wb_url.url)

        inputreq = RewriteInputRequest(environ, urlkey, wb_url.url,
                                       self.content_rewriter)

        inputreq.include_post_query(wb_url.url)

        mod_url = None
        use_206 = False
        rangeres = None

        readd_range = False
        async_record_url = None

        if kwargs.get('type') in ('record', 'patch'):
            rangeres = inputreq.extract_range()

            if rangeres:
                mod_url, start, end, use_206 = rangeres

                # if bytes=0- Range request,
                # simply remove the range and still proxy
                if start == 0 and not end and use_206:
                    wb_url.url = mod_url
                    inputreq.url = mod_url

                    del environ['HTTP_RANGE']
                    readd_range = True
                else:
                    async_record_url = mod_url

        skip = async_record_url is not None

        setcookie_headers = None
        if self.cookie_tracker:
            cookie_key = self.get_cookie_key(kwargs)
            res = self.cookie_tracker.get_cookie_headers(wb_url.url, urlrewriter, cookie_key)
            inputreq.extra_cookie, setcookie_headers = res

        r = self._do_req(inputreq, wb_url, kwargs, skip)

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
            raise UpstreamException(r.status_code, url=wb_url.url, details=details)

        if async_record_url:
            environ.pop('HTTP_RANGE', '')
            new_wb_url = copy(wb_url)
            new_wb_url.url = async_record_url

            gevent.spawn(self._do_async_req,
                         inputreq,
                         new_wb_url,
                         kwargs,
                         False)

        stream = BufferedReader(r.raw, block_size=BUFF_SIZE)
        record = self.loader.parse_record_stream(stream)

        memento_dt = r.headers.get('Memento-Datetime')
        target_uri = r.headers.get('WARC-Target-URI')

        cdx = CDXObject()
        cdx['urlkey'] = urlkey
        cdx['timestamp'] = http_date_to_timestamp(memento_dt)
        cdx['url'] = target_uri

        self._add_custom_params(cdx, r.headers, kwargs)

        if readd_range:
            content_length = (record.http_headers.
                              get_header('Content-Length'))
            try:
                content_length = int(content_length)
                record.http_headers.add_range(0, content_length,
                                                   content_length)
            except (ValueError, TypeError):
                pass

        if self.is_ajax(environ):
            head_insert_func = None
            urlrewriter.rewrite_opts['is_ajax'] = True
        else:
            top_url = self.get_top_url(full_prefix, wb_url, cdx, kwargs)
            head_insert_func = (self.head_insert_view.
                                    create_insert_func(wb_url,
                                                       full_prefix,
                                                       host_prefix,
                                                       top_url,
                                                       environ,
                                                       self.framed_replay))

        cookie_rewriter = None
        if self.cookie_tracker:
            cookie_rewriter = self.cookie_tracker.get_rewriter(urlrewriter,
                                                               cookie_key)

        result = self.content_rewriter.rewrite_content(urlrewriter,
                                               record.http_headers,
                                               record.raw_stream,
                                               head_insert_func,
                                               urlkey,
                                               cdx,
                                               cookie_rewriter,
                                               environ)

        status_headers, gen, is_rw = result

        if setcookie_headers:
            status_headers.headers.extend(setcookie_headers)

        if ' ' not in status_headers.statusline:
            status_headers.statusline += ' None'

        self._add_memento_links(urlrewriter, full_prefix, memento_dt, status_headers)

        #if cdx['timestamp'] != wb_url.timestamp:
        status_headers.headers.append(('Content-Location', urlrewriter.get_new_url(timestamp=cdx['timestamp'],
                                                                                   url=cdx['url'])))

        #gen = buffer_iter(status_headers, gen)

        return WbResponse(status_headers, gen)

    def _add_memento_links(self, urlrewriter, full_prefix, memento_dt, status_headers):
        wb_url = urlrewriter.wburl
        status_headers.headers.append(('Memento-Datetime', memento_dt))

        memento_url = full_prefix + wb_url._original_url
        timegate_url = urlrewriter.get_new_url(timestamp='')

        link = []
        link.append(MementoUtils.make_link(timegate_url, 'timegate'))
        link.append(MementoUtils.make_memento_link(memento_url, 'memento', memento_dt))
        link_str = ', '.join(link)

        status_headers.headers.append(('Link', link_str))

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
        if ue.status_code == 404:
            return self._not_found_response(environ, ue.url)

        else:
            status = str(ue.status_code) + ' ' + HTTP_STATUS_CODES.get(ue.status_code, 'Unknown Error')
            return self._error_response(environ, ue.url, ue.msg,
                                        status=status)

    def _not_found_response(self, environ, url):
        resp = self.not_found_view.render_to_string(environ, url=url)

        return WbResponse.text_response(resp, status='404 Not Found', content_type='text/html')

    def _error_response(self, environ, msg='', details='', status='404 Not Found'):
        resp = self.error_view.render_to_string(environ,
                                                err_msg=msg,
                                                err_details=details)

        return WbResponse.text_response(resp, status=status, content_type='text/html')


    def _do_req(self, inputreq, wb_url, kwargs, skip):
        req_data = inputreq.reconstruct_request(wb_url.url)

        headers = {'Content-Length': str(len(req_data)),
                   'Content-Type': 'application/request'}

        if skip:
            headers['Recorder-Skip'] = '1'

        if wb_url.is_latest_replay():
            closest = 'now'
        else:
            closest = wb_url.timestamp

        params = {}
        params['url'] = wb_url.url
        params['closest'] = closest

        if wb_url.mod == 'vi_':
            params['content_type'] = self.VIDEO_INFO_CONTENT_TYPE

        upstream_url = self.get_upstream_url(wb_url, kwargs, params)

        r = requests.post(upstream_url,
                          data=BytesIO(req_data),
                          headers=headers,
                          stream=True)

        return r

    def do_query(self, wb_url, kwargs):
        params = {}
        params['url'] = wb_url.url
        params['output'] = 'json'
        params['from'] = wb_url.timestamp
        params['to'] = wb_url.end_timestamp

        upstream_url = self.get_upstream_url(wb_url, kwargs, params)
        upstream_url = upstream_url.replace('/resource/postreq', '/index')

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

    def get_base_url(self, wb_url, kwargs):
        type = kwargs.get('type')
        return self.paths[type].format(**kwargs)

    def get_upstream_url(self, wb_url, kwargs, params):
        base_url = self.get_base_url(wb_url, kwargs)
        param_str = urlencode(params, True)
        if param_str:
            q_char = '&' if '?' in base_url else '?'
            base_url += q_char + param_str
        return base_url

    def get_cookie_key(self, kwargs):
        raise NotImplemented()

    def _add_custom_params(self, cdx, headers, kwargs):
        cdx['is_live'] = 'true'
        pass

    def get_top_frame_params(self, wb_url, kwargs):
        return None

    def handle_custom_response(self, environ, wb_url, full_prefix, host_prefix, kwargs):
        if wb_url.is_query():
            return self.handle_query(environ, wb_url, kwargs)

        if self.is_framed_replay(wb_url):
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
