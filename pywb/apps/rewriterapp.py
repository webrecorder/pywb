import requests

from werkzeug.http import HTTP_STATUS_CODES
from six.moves.urllib.parse import urlencode, urlsplit, urlunsplit

from pywb.rewrite.default_rewriter import DefaultRewriter, RewriterWithJSProxy

from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.url_rewriter import UrlRewriter, IdentityUrlRewriter

from pywb.utils.wbexception import WbException
from pywb.utils.canonicalize import canonicalize
from pywb.utils.loaders import extract_client_cookie
from pywb.utils.io import BUFF_SIZE, OffsetLimitReader
from pywb.utils.memento import MementoUtils

from warcio.timeutils import http_date_to_timestamp, timestamp_to_http_date
from warcio.bufferedreaders import BufferedReader
from warcio.recordloader import ArcWarcRecordLoader

from pywb.warcserver.index.cdxobject import CDXObject
from pywb.apps.wbrequestresponse import WbResponse

from pywb.rewrite.rewriteinputreq import RewriteInputRequest
from pywb.rewrite.templateview import JinjaEnv, HeadInsertView, TopFrameView, BaseInsertView


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
#class Rewriter(RewriteDASHMixin, RewriteAMFMixin, RewriteContent):
#    pass


# ============================================================================
class RewriterApp(object):
    VIDEO_INFO_CONTENT_TYPE = 'application/vnd.youtube-dl_formats+json'

    DEFAULT_CSP = "default-src 'unsafe-eval' 'unsafe-inline' 'self' data: blob: mediastream: ws: wss: ; form-action 'self'"

    def __init__(self, framed_replay=False, jinja_env=None, config=None, paths=None):
        self.loader = ArcWarcRecordLoader()

        self.config = config or {}
        self.paths = paths or {}

        self.framed_replay = framed_replay

        if framed_replay:
            self.frame_mod = ''
            self.replay_mod = 'mp_'
        else:
            self.frame_mod = None
            self.replay_mod = ''

        self.default_rw = DefaultRewriter(replay_mod=self.replay_mod,
                                          config=config)

        self.js_proxy_rw = RewriterWithJSProxy(replay_mod=self.replay_mod)

        if not jinja_env:
            jinja_env = JinjaEnv(globals={'static_path': 'static'})

        self.jinja_env = jinja_env

        self.redirect_to_exact = config.get('redirect_to_exact')

        self.banner_view = BaseInsertView(self.jinja_env, self._html_templ('banner_html'))

        self.head_insert_view = HeadInsertView(self.jinja_env,
                                               self._html_templ('head_insert_html'),
                                               self.banner_view)

        self.frame_insert_view = TopFrameView(self.jinja_env,
                                               self._html_templ('frame_insert_html'),
                                               self.banner_view)

        self.error_view = BaseInsertView(self.jinja_env, self._html_templ('error_html'))
        self.not_found_view = BaseInsertView(self.jinja_env, self._html_templ('not_found_html'))
        self.query_view = BaseInsertView(self.jinja_env, self._html_templ('query_html'))

        self.use_js_obj_proxy = config.get('use_js_obj_proxy', True)

        self.cookie_tracker = None

        self.enable_memento = self.config.get('enable_memento')

        csp_header = self.config.get('csp-header', self.DEFAULT_CSP)
        if csp_header:
            self.csp_header = ('Content-Security-Policy', csp_header)
        else:
            self.csp_header = None

        # deprecated: Use X-Forwarded-Proto header instead!
        self.force_scheme = config.get('force_scheme')

    def add_csp_header(self, wb_url, status_headers):
        if self.csp_header and wb_url.mod == self.replay_mod:
            status_headers.headers.append(self.csp_header)

    def _html_templ(self, name):
        value = self.config.get(name)
        if not value:
            value = name.replace('_html', '.html')
        return value

    def is_framed_replay(self, wb_url):
        return (self.framed_replay and
                wb_url.mod == self.frame_mod and
                wb_url.is_replay())

    def _check_accept_dt(self, wb_url, environ):
        is_timegate = False
        if wb_url.is_latest_replay():
            accept_dt = environ.get('HTTP_ACCEPT_DATETIME')
            is_timegate = True
            if accept_dt:
                try:
                    wb_url.timestamp = http_date_to_timestamp(accept_dt)
                except:
                    raise UpstreamException(400, url=wb_url.url, details='Invalid Accept-Datetime')
                    #return WbResponse.text_response('Invalid Accept-Datetime', status='400 Bad Request')

                wb_url.type = wb_url.REPLAY

        return is_timegate

    def _check_range(self, inputreq, wb_url):
        skip_record = False
        range_start = None
        range_end = None

        rangeres = inputreq.extract_range()

        if not rangeres:
            return range_start, range_end, skip_record

        mod_url, start, end, use_206 = rangeres

        # remove the range and still proxy
        if not use_206:
            return range_start, range_end, skip_record

        wb_url.url = mod_url
        inputreq.url = mod_url

        range_start = start
        range_end = end

        #if start with 0, load from upstream, but add range after
        if start == 0:
            del inputreq.env['HTTP_RANGE']
        else:
            skip_record = True

        return range_start, range_end, skip_record

    def _add_range(self, record, wb_url, range_start, range_end):
        if range_end is None and range_start is None:
            return

        if record.http_headers.get_statuscode() != '200':
            return

        content_length = (record.http_headers.
                          get_header('Content-Length'))

        if content_length is None:
            return

        content_length = content_length.split(',')[0]

        try:
            content_length = int(content_length)
            if not range_end:
                range_end = content_length - 1

            if range_start >= content_length or range_end >= content_length:
                details = 'Invalid Range: {0} >= {2} or {1} >= {2}'.format(range_start, range_end, content_length)
                try:
                    r.raw.close()
                except:
                    pass

                raise UpstreamException(416, url=wb_url.url, details=details)

            range_len = range_end - range_start + 1
            record.http_headers.add_range(range_start, range_len,
                                          content_length)

            record.http_headers.replace_header('Content-Length', str(range_len))

            record.raw_stream = OffsetLimitReader(record.raw_stream, range_start, range_len)
            return True

        except (ValueError, TypeError):
            pass

    def send_redirect(self, new_path, url_parts, urlrewriter):
        scheme, netloc, path, query, frag = url_parts
        path = new_path
        url = urlunsplit((scheme, netloc, path, query, frag))
        resp = WbResponse.redir_response(urlrewriter.rewrite(url),
                                         '307 Temporary Redirect')

        if self.enable_memento:
            resp.status_headers['Link'] = MementoUtils.make_link(url, 'original')

        return resp

    def render_content(self, wb_url, kwargs, environ):
        wb_url = wb_url.replace('#', '%23')
        wb_url = WbUrl(wb_url)

        proto = environ.get('HTTP_X_FORWARDED_PROTO', self.force_scheme)

        if proto:
            environ['wsgi.url_scheme'] = proto

        is_timegate = self._check_accept_dt(wb_url, environ)

        host_prefix = self.get_host_prefix(environ)
        rel_prefix = self.get_rel_prefix(environ)
        full_prefix = host_prefix + rel_prefix

        is_proxy = ('wsgiprox.proxy_host' in environ)

        response = self.handle_custom_response(environ, wb_url,
                                               full_prefix, host_prefix,
                                               kwargs)

        if response:
            return self.format_response(response, wb_url, full_prefix, is_timegate, is_proxy)

        if is_proxy:
            environ['pywb_proxy_magic'] = environ['wsgiprox.proxy_host']
            urlrewriter = IdentityUrlRewriter(wb_url, '')
            framed_replay = False

        else:
            urlrewriter = UrlRewriter(wb_url,
                                      prefix=full_prefix,
                                      full_prefix=full_prefix,
                                      rel_prefix=rel_prefix)

            framed_replay = self.framed_replay

        url_parts = urlsplit(wb_url.url)
        if not url_parts.path:
            return self.send_redirect('/', url_parts, urlrewriter)

        self.unrewrite_referrer(environ, full_prefix)

        urlkey = canonicalize(wb_url.url)

        environ['pywb.host_prefix'] = host_prefix

        if self.use_js_obj_proxy:
            content_rw = self.js_proxy_rw
        else:
            content_rw = self.default_rw

        inputreq = RewriteInputRequest(environ, urlkey, wb_url.url, content_rw)

        inputreq.include_method_query(wb_url.url)

        range_start, range_end, skip_record = self._check_range(inputreq, wb_url)

        setcookie_headers = None
        if self.cookie_tracker:
            cookie_key = self.get_cookie_key(kwargs)
            res = self.cookie_tracker.get_cookie_headers(wb_url.url, urlrewriter, cookie_key)
            inputreq.extra_cookie, setcookie_headers = res

        r = self._do_req(inputreq, wb_url, kwargs, skip_record)

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

        cdx = CDXObject(r.headers.get('Warcserver-Cdx').encode('utf-8'))

        cdx_url_parts = urlsplit(cdx['url'])

        if cdx_url_parts.path.endswith('/') and not url_parts.path.endswith('/'):
            # add trailing slash
            new_path = url_parts.path + '/'

            try:
                r.raw.close()
            except:
                pass

            return self.send_redirect(new_path, url_parts, urlrewriter)

        stream = BufferedReader(r.raw, block_size=BUFF_SIZE)
        record = self.loader.parse_record_stream(stream,
                                                 ensure_http_headers=True)

        memento_dt = r.headers.get('Memento-Datetime')
        target_uri = r.headers.get('WARC-Target-URI')

        #cdx['urlkey'] = urlkey
        #cdx['timestamp'] = http_date_to_timestamp(memento_dt)
        #cdx['url'] = target_uri

        set_content_loc = False

        # Check if Fuzzy Match
        if target_uri != wb_url.url and cdx.get('is_fuzzy') == '1':
            set_content_loc = True

        # if redir to exact, redir if url or ts are different
        if self.redirect_to_exact:
            if (set_content_loc or
                (wb_url.timestamp != cdx.get('timestamp') and not cdx.get('is_live'))):

                new_url = urlrewriter.get_new_url(url=target_uri,
                                                  timestamp=cdx['timestamp'],
                                                  mod=wb_url.mod)

                resp = WbResponse.redir_response(new_url, '307 Temporary Redirect')
                if self.enable_memento:
                    if is_timegate and not is_proxy:
                        self._add_memento_links(target_uri, full_prefix,
                                                memento_dt, cdx['timestamp'],
                                                resp.status_headers,
                                                is_timegate, is_proxy)

                    else:
                        resp.status_headers['Link'] = MementoUtils.make_link(target_uri, 'original')

                return resp

        self._add_custom_params(cdx, r.headers, kwargs, record)

        if self._add_range(record, wb_url, range_start, range_end):
            wb_url.mod = 'id_'

        is_ajax = self.is_ajax(environ)

        if is_ajax:
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
                                                       framed_replay,
                                                       coll=kwargs.get('coll', ''),
                                                       replay_mod=self.replay_mod,
                                                       config=self.config))

        cookie_rewriter = None
        if self.cookie_tracker:
            cookie_rewriter = self.cookie_tracker.get_rewriter(urlrewriter,
                                                               cookie_key)

        urlrewriter.rewrite_opts['ua_string'] = environ.get('HTTP_USER_AGENT')

        result = content_rw(record, urlrewriter, cookie_rewriter, head_insert_func, cdx, environ)

        status_headers, gen, is_rw = result

        if setcookie_headers:
            status_headers.headers.extend(setcookie_headers)

        if ' ' not in status_headers.statusline:
            status_headers.statusline += ' None'

        if not is_ajax and self.enable_memento:
            self._add_memento_links(cdx['url'], full_prefix,
                                    memento_dt, cdx['timestamp'], status_headers,
                                    is_timegate, is_proxy, cdx.get('source-coll'))

            set_content_loc = True

        if set_content_loc and not self.redirect_to_exact:
            status_headers.headers.append(('Content-Location', urlrewriter.get_new_url(timestamp=cdx['timestamp'],
                                                                                       url=cdx['url'])))
        if not is_proxy:
            self.add_csp_header(wb_url, status_headers)

        response = WbResponse(status_headers, gen)

        return response

    def format_response(self, response, wb_url, full_prefix, is_timegate, is_proxy):
        memento_ts = None
        if not isinstance(response, WbResponse):
            content_type = 'text/html'

            # if not replay outer frame, specify utf-8 charset
            if not self.is_framed_replay(wb_url):
                content_type += '; charset=utf-8'
            else:
                memento_ts = wb_url.timestamp

            response = WbResponse.text_response(response, content_type=content_type)

        if self.enable_memento:
            self._add_memento_links(wb_url.url, full_prefix, None, memento_ts,
                                    response.status_headers, is_timegate, is_proxy)
        return response

    def _add_memento_links(self, url, full_prefix, memento_dt, memento_ts,
                           status_headers, is_timegate, is_proxy, coll=None):

        # memento url + header
        if not memento_dt and memento_ts:
            memento_dt = timestamp_to_http_date(memento_ts)

        if memento_dt:
            status_headers.headers.append(('Memento-Datetime', memento_dt))

            if is_proxy:
                memento_url = url
            else:
                memento_url = full_prefix + memento_ts + self.replay_mod
                memento_url += '/' + url
        else:
            memento_url = None

        timegate_url, timemap_url = self._get_timegate_timemap(url, full_prefix)

        link = []
        if not is_proxy:
            link.append(MementoUtils.make_link(url, 'original'))
            link.append(MementoUtils.make_link(timegate_url, 'timegate'))
            link.append(MementoUtils.make_link(timemap_url, 'timemap'))

        if memento_dt:
            link.append(MementoUtils.make_memento_link(memento_url, 'memento', memento_dt, coll))

        link_str = ', '.join(link)

        status_headers.headers.append(('Link', link_str))

        if is_timegate:
            status_headers.headers.append(('Vary', 'accept-datetime'))

    def _get_timegate_timemap(self, url, full_prefix):
        # timegate url
        timegate_url = full_prefix
        if self.replay_mod:
            timegate_url += self.replay_mod + '/'

        timegate_url += url

        # timemap url
        timemap_url = full_prefix + 'timemap/link/' + url
        return timegate_url, timemap_url

    def get_top_url(self, full_prefix, wb_url, cdx, kwargs):
        top_url = full_prefix
        top_url += wb_url.to_str(mod='')
        return top_url

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


    def _do_req(self, inputreq, wb_url, kwargs, skip_record):
        req_data = inputreq.reconstruct_request(wb_url.url)

        headers = {'Content-Length': str(len(req_data)),
                   'Content-Type': 'application/request'}

        if skip_record:
            headers['Recorder-Skip'] = '1'

        if wb_url.is_latest_replay():
            closest = 'now'
        else:
            closest = wb_url.timestamp

        params = {}
        params['url'] = wb_url.url
        params['closest'] = closest
        params['matchType'] = 'exact'

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
        params['output'] = kwargs.get('output', 'json')
        params['from'] = wb_url.timestamp
        params['to'] = wb_url.end_timestamp

        upstream_url = self.get_upstream_url(wb_url, kwargs, params)
        upstream_url = upstream_url.replace('/resource/postreq', '/index')

        r = requests.get(upstream_url)

        return r

    def make_timemap(self, wb_url, res, full_prefix, output):
        wb_url.type = wb_url.QUERY

        content_type = res.headers.get('Content-Type')
        text = res.text

        if not res.text:
            status = '404 Not Found'

        elif res.status_code:
            status = str(res.status_code) + ' ' + res.reason

            if res.status_code == 200 and output == 'link':
                timegate, timemap = self._get_timegate_timemap(wb_url.url, full_prefix)

                text = MementoUtils.wrap_timemap_header(wb_url.url,
                                                        timegate,
                                                        timemap,
                                                        res.text)
        return WbResponse.text_response(text,
                                        content_type=content_type,
                                        status=status)

    def handle_timemap(self, wb_url, kwargs, full_prefix):
        output = kwargs.get('output')
        res = self.do_query(wb_url, kwargs)
        return self.make_timemap(wb_url, res, full_prefix, output)

    def handle_query(self, environ, wb_url, kwargs, full_prefix):
        prefix = self.get_full_prefix(environ)

        params = dict(url=wb_url.url,
                      prefix=prefix)

        return self.query_view.render_to_string(environ, **params)

    def get_host_prefix(self, environ):
        scheme = environ['wsgi.url_scheme'] + '://'

        # proxy
        host = environ.get('wsgiprox.proxy_host')
        if host:
            return scheme + host

        # default
        host = environ.get('HTTP_HOST')
        if host:
            return scheme + host

        # if no host
        host = environ['SERVER_NAME']
        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
                host += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
                host += ':' + environ['SERVER_PORT']

        return scheme + host

    def get_rel_prefix(self, environ):
        #return request.script_name
        return environ.get('SCRIPT_NAME') + '/'

    def get_full_prefix(self, environ):
        return self.get_host_prefix(environ) + self.get_rel_prefix(environ)

    def unrewrite_referrer(self, environ, full_prefix):
        referrer = environ.get('HTTP_REFERER')
        if not referrer:
            return False

        if referrer.startswith(full_prefix):
            referrer = referrer[len(full_prefix):]
            if referrer:
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

    def _add_custom_params(self, cdx, headers, kwargs, record):
        pass

    def get_top_frame_params(self, wb_url, kwargs):
        return None

    def handle_custom_response(self, environ, wb_url, full_prefix, host_prefix, kwargs):
        if kwargs.get('output'):
            return self.handle_timemap(wb_url, kwargs, full_prefix)

        if wb_url.is_query():
            return self.handle_query(environ, wb_url, kwargs, full_prefix)

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
