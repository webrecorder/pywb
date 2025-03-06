from io import BytesIO

import requests
from fakeredis import FakeStrictRedis
from six.moves.urllib.parse import unquote, urlencode, urlsplit, urlunsplit, parse_qsl
from warcio.bufferedreaders import BufferedReader
from warcio.recordloader import ArcWarcRecordLoader
from warcio.timeutils import http_date_to_timestamp, timestamp_to_http_date

from pywb.apps.wbrequestresponse import WbResponse
from pywb.rewrite.cookies import CookieTracker
from pywb.rewrite.default_rewriter import DefaultRewriter, RewriterWithJSProxy
from pywb.rewrite.rewriteinputreq import RewriteInputRequest
from pywb.rewrite.templateview import BaseInsertView, HeadInsertView, JinjaEnv, TopFrameView
from pywb.rewrite.url_rewriter import IdentityUrlRewriter, UrlRewriter
from pywb.rewrite.wburl import WbUrl
from pywb.utils.canonicalize import canonicalize
from pywb.utils.io import BUFF_SIZE, OffsetLimitReader, no_except_close
from pywb.utils.memento import MementoUtils
from pywb.utils.wbexception import NotFoundException, UpstreamException
from pywb.warcserver.index.cdxobject import CDXObject


# ============================================================================
class RewriterApp(object):
    """Primary application for rewriting the content served by pywb (if it is to be rewritten).

    This class is also responsible rendering the archives templates
    """
    VIDEO_INFO_CONTENT_TYPE = 'application/vnd.youtube-dl_formats+json'

    DEFAULT_CSP = "default-src 'unsafe-eval' 'unsafe-inline' 'self' data: blob: mediastream: ws: wss: ; form-action 'self'"

    def __init__(self, framed_replay=False, jinja_env=None, config=None, paths=None):
        """Initialize a new instance of RewriterApp

        :param bool framed_replay: Is rewriting happening in framed replay mode
        :param JinjaEnv|None jinja_env: Optional JinjaEnv instance to be used for
            rendering static files
        :param dict|None config: Optional config dictionary
        :param dict|None paths: Optional dictionary containing a mapping
            of path names to URLs
        """
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

        self.enable_prefer = self.config.get('enable_prefer', False)

        self.default_rw = DefaultRewriter(replay_mod=self.replay_mod,
                                          config=config)

        self.js_proxy_rw = RewriterWithJSProxy(replay_mod=self.replay_mod)

        if not jinja_env:
            jinja_env = JinjaEnv(globals={'static_path': 'static'},
                                 extensions=['jinja2.ext.i18n'])
            jinja_env.jinja_env.install_null_translations()

        self.jinja_env = jinja_env
        self.loc_map = {}

        self.jinja_env.init_loc(self.config.get('locales_root_dir'),
                                self.config.get('locales'),
                                self.loc_map,
                                self.config.get('default_locale'))

        self.redirect_to_exact = config.get('redirect_to_exact')

        self.banner_view = BaseInsertView(self.jinja_env, self._html_templ('banner_html'))
        self.custom_banner_view = BaseInsertView(self.jinja_env, self._html_templ('custom_banner_html'))

        self.head_insert_view = HeadInsertView(self.jinja_env,
                                               self._html_templ('head_insert_html'),
                                               self.custom_banner_view)

        self.client_side_replay = self.config.get('client_side_replay', False)

        self.frame_insert_view = TopFrameView(self.jinja_env,
                                              self._html_templ('frame_insert_html'),
                                              self.banner_view)

        self.error_view = BaseInsertView(self.jinja_env, self._html_templ('error_html'))
        self.not_found_view = BaseInsertView(self.jinja_env, self._html_templ('not_found_html'))
        self.query_view = BaseInsertView(self.jinja_env, self._html_templ('query_html'))

        self.use_js_obj_proxy = config.get('use_js_obj_proxy', True)

        self.cookie_tracker = self._init_cookie_tracker()

        self.enable_memento = self.config.get('enable_memento')

        self.static_prefix = self.config.get('static_prefix', 'static')

        csp_header = self.config.get('csp-header', self.DEFAULT_CSP)
        if csp_header:
            self.csp_header = ('Content-Security-Policy', csp_header)
        else:
            self.csp_header = None

        # deprecated: Use X-Forwarded-Proto header instead!
        self.force_scheme = config.get('force_scheme')

    def _init_cookie_tracker(self, redis=None):
        """Initialize the CookieTracker

        :param redis: Optional redis instance to be used
        Defaults to FakeStrictRedis
        :return: The initialized cookie tracker
        :rtype: CookieTracker
        """
        if redis is None:
            redis = FakeStrictRedis()
        return CookieTracker(redis)

    def add_csp_header(self, wb_url, status_headers):
        """Adds Content-Security-Policy headers to the supplied
        StatusAndHeaders instance if the wb_url's mod is equal
        to the replay mod

        :param WbUrl wb_url: The WbUrl for the URL being operated on
        :param warcio.StatusAndHeaders status_headers: The status and
        headers instance for the reply to the URL
        """
        if self.csp_header and wb_url.mod == self.replay_mod:
            status_headers.headers.append(self.csp_header)

    def _html_templ(self, name):
        """Returns the html file name for the supplied
        html template name.

        :param str name: The name of the html template
        :return: The file name for the template
        :rtype: str|None
        """
        value = self.config.get(name)
        if not value:
            value = name.replace('_html', '.html')
        return value

    def is_framed_replay(self, wb_url):
        """Returns T/F indicating if the rewriter app is configured to
        be operating in framed replay mode and the supplied WbUrl
        is also operating in framed replay mode

        :param WbUrl wb_url: The WbUrl instance to check
        :return: T/F if in framed replay mode
        :rtype: bool
        """
        return (self.framed_replay and
                wb_url.mod == self.frame_mod and
                wb_url.is_replay())

    def _check_accept_dt(self, wb_url, environ):
        """Returns T/F indicating if the supplied WbUrl instance
        is for a timegate request

        :param WbUrl wb_url: The URL to be checked
        :param dict environ: The wsgi environment object for the request
        :return: T/F indicating if the WbUrl is for timegate request
        :rtype: bool
        """
        is_timegate = False
        if wb_url.is_latest_replay():
            accept_dt = environ.get('HTTP_ACCEPT_DATETIME')
            is_timegate = True
            if accept_dt:
                try:
                    wb_url.timestamp = http_date_to_timestamp(accept_dt)
                except Exception:
                    raise UpstreamException(400, url=wb_url.url, details='Invalid Accept-Datetime')
                    # return WbResponse.text_response('Invalid Accept-Datetime', status='400 Bad Request')

                wb_url.type = wb_url.REPLAY

            elif 'pywb_proxy_default_timestamp' in environ:
                wb_url.timestamp = environ['pywb_proxy_default_timestamp']
                wb_url.type = wb_url.REPLAY

        return is_timegate

    def _get_prefer_mod(self, wb_url, environ, content_rw, is_proxy):
        """Returns the default rewrite modifier and rewrite modifier based on the
        value of the Prefer HTTP header if it is present

        :param WbUrl wb_url: The WbUrl for the URL being rewritten
        :param dict environ: The WSGI environment dictionary for the request
        :param content_rw: The content rewriter instance
        :param bool is_proxy: Is the rewrite operating in proxy mode
        :return: A tuple containing the default rewrite modifier and rewrite modifier based
        on the  value of the Prefer HTTP header if it is present
        :rtype: tuple[str|None, str|None]
        """
        if not self.enable_prefer:
            return None, None

        prefer = environ.get('HTTP_PREFER')
        if not prefer:
            return None, content_rw.mod_to_prefer(wb_url.mod)

        mod = content_rw.prefer_to_mod(prefer)

        if mod is None:
            raise UpstreamException(400, url=wb_url.url, details='Invalid Prefer: ' + prefer)

        if is_proxy and mod == self.replay_mod:
            mod = 'bn_'
            prefer = content_rw.mod_to_prefer('bn_')

        return mod, prefer

    def _check_range(self, inputreq, wb_url):
        """Checks the input request if it is a range request returning
        the start and end of the range as well as T/F if the request should
        be skipped as a tuple.

        :param RewriteInputRequest inputreq: The input request to check range
        :param WbUrl wb_url: The WbUrl associated with the request
        :return: A tuple with the start, end, and T/F should skip request
        :rtype: tuple[int|None, int|None, bool]
        """
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

        # if start with 0, load from upstream, but add range after
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

    def prepare_env(self, environ):
        """ setup environ path prefixes and scheme """
        if 'pywb.host_prefix' in environ:
            return

        proto = environ.get('HTTP_X_FORWARDED_PROTO', self.force_scheme)

        if proto:
            environ['wsgi.url_scheme'] = proto

        environ['pywb.host_prefix'] = self.get_host_prefix(environ)
        environ['pywb.app_prefix'] = environ.get('SCRIPT_NAME', '')
        environ['pywb.static_prefix'] = environ['pywb.host_prefix'] + environ['pywb.app_prefix'] + '/' + self.static_prefix

    def render_content(self, wb_url, kwargs, environ):
        wb_url = wb_url.replace('#', '%23')
        wb_url = WbUrl(wb_url)

        history_page = environ.pop('HTTP_X_WOMBAT_HISTORY_PAGE', '')
        if history_page:
            wb_url.url = history_page
            is_ajax = True
        else:
            is_ajax = self.is_ajax(environ)

        is_timegate = self._check_accept_dt(wb_url, environ)

        self.prepare_env(environ)

        host_prefix = environ['pywb.host_prefix']
        rel_prefix = self.get_rel_prefix(environ)
        full_prefix = host_prefix + rel_prefix

        pywb_static_prefix = environ['pywb.static_prefix'] + '/'
        is_proxy = ('wsgiprox.proxy_host' in environ)

        # if OPTIONS in proxy mode, just generate the proxy responss
        if is_proxy and self.is_preflight(environ):
            return WbResponse.options_response(environ)

        if self.use_js_obj_proxy:
            content_rw = self.js_proxy_rw
        else:
            content_rw = self.default_rw

        # no redirects if in proxy
        redirect_to_exact = self.redirect_to_exact and not is_proxy

        # Check Prefer
        pref_mod, pref_applied = self._get_prefer_mod(wb_url, environ,
                                                      content_rw, is_proxy)

        response = None
        keep_frame_response = False

        # prefer overrides custom response?
        if pref_mod is not None:
            # fast-redirect to preferred
            if redirect_to_exact and not is_timegate and pref_mod != wb_url.mod:
                new_url = full_prefix + wb_url.to_str(mod=pref_mod)
                headers = [('Preference-Applied', pref_applied),
                           ('Vary', 'Prefer')]

                return WbResponse.redir_response(new_url,
                                                 '307 Temporary Redirect',
                                                 headers=headers)
            else:
                wb_url.mod = pref_mod
        else:
            if kwargs.get('output'):
                response = self.handle_timemap(wb_url, kwargs, full_prefix)

            elif wb_url.is_query():
                response = self.handle_query(environ, wb_url, kwargs, full_prefix)

            else:
                response = self.handle_custom_response(environ, wb_url,
                                                       full_prefix, host_prefix,
                                                       kwargs)

                keep_frame_response = (not kwargs.get('no_timegate_check') and is_timegate and not is_proxy) or redirect_to_exact


        if response and not keep_frame_response:
            return self.format_response(response, wb_url, full_prefix, is_timegate, is_proxy)

        if is_proxy:
            environ['pywb_proxy_magic'] = environ['wsgiprox.proxy_host']
            urlrewriter = IdentityUrlRewriter(wb_url, '')
            framed_replay = False

        else:
            urlrewriter = UrlRewriter(wb_url,
                                      prefix=full_prefix,
                                      full_prefix=full_prefix,
                                      rel_prefix=rel_prefix,
                                      pywb_static_prefix=pywb_static_prefix)

            framed_replay = self.framed_replay

        url_parts = urlsplit(wb_url.url)
        if not url_parts.path:
            return self.send_redirect('/', url_parts, urlrewriter)

        self.unrewrite_referrer(environ, full_prefix)

        urlkey = canonicalize(wb_url.url)

        inputreq = RewriteInputRequest(environ, urlkey, wb_url.url, content_rw)

        inputreq.include_method_query(wb_url.url)

        range_start, range_end, skip_record = self._check_range(inputreq, wb_url)

        setcookie_headers = None
        cookie_key = None
        if self.cookie_tracker:
            cookie_key = self.get_cookie_key(kwargs)
            if cookie_key:
                res = self.cookie_tracker.get_cookie_headers(wb_url.url,
                                                             urlrewriter,
                                                             cookie_key,
                                                             environ.get('HTTP_COOKIE', ''))
                inputreq.extra_cookie, setcookie_headers = res

        r = self._do_req(inputreq, wb_url, kwargs, skip_record)

        if r.status_code >= 400:
            error = None
            try:
                error = r.raw.read()
            except Exception:
                pass
            finally:
                no_except_close(r.raw)

            if error:
                error = error.decode('utf-8')
            else:
                error = ''

            details = dict(args=kwargs, error=error)
            if r.status_code == 404:
                raise NotFoundException(url=wb_url.url, msg=details)

            else:
                raise UpstreamException(r.status_code, url=wb_url.url, details=details)

        cdx = CDXObject(r.headers.get('Warcserver-Cdx').encode('utf-8'))

        cdx_url_parts = urlsplit(cdx['url'])

        if cdx_url_parts.path.endswith('/') and not url_parts.path.endswith('/'):
            # add trailing slash
            new_path = url_parts.path + '/'

            no_except_close(r.raw)

            return self.send_redirect(new_path, url_parts, urlrewriter)


        # only redirect to exact if not live, otherwise set to false
        redirect_to_exact = redirect_to_exact and not cdx.get('is_live')

        # return top-frame timegate response, with timestamp from cdx
        if response and keep_frame_response and (not redirect_to_exact or not is_timegate):
            no_except_close(r.raw)
            return self.format_response(response, wb_url, full_prefix, is_timegate, is_proxy, cdx['timestamp'])

        stream = BufferedReader(r.raw, block_size=BUFF_SIZE)
        record = self.loader.parse_record_stream(stream,
                                                 ensure_http_headers=True)

        memento_dt = r.headers.get('Memento-Datetime')
        target_uri = r.headers.get('WARC-Target-URI')

        # cdx['urlkey'] = urlkey
        # cdx['timestamp'] = http_date_to_timestamp(memento_dt)
        # cdx['url'] = target_uri

        set_content_loc = False

        # Check if Fuzzy Match
        if target_uri != wb_url.url and cdx.get('is_fuzzy') == '1':
            set_content_loc = True

        # if redirect to exact timestamp (only set if not live)
        if redirect_to_exact:
            if set_content_loc or is_timegate or wb_url.timestamp != cdx.get('timestamp'):
                new_url = urlrewriter.get_new_url(url=target_uri,
                                                  timestamp=cdx['timestamp'],
                                                  mod=wb_url.mod)

                resp = WbResponse.redir_response(new_url, '307 Temporary Redirect')
                if self.enable_memento:
                    if is_timegate and not is_proxy:
                        self._add_memento_links(target_uri, full_prefix,
                                                memento_dt, cdx['timestamp'],
                                                resp.status_headers,
                                                is_timegate, is_proxy,
                                                pref_applied=pref_applied,
                                                mod=pref_mod,
                                                is_memento=False)

                    else:
                        resp.status_headers['Link'] = MementoUtils.make_link(target_uri, 'original')

                return resp

        self._add_custom_params(cdx, r.headers, kwargs, record)

        if self._add_range(record, wb_url, range_start, range_end):
            wb_url.mod = 'id_'

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
                                                   metadata=kwargs.get('metadata', {}),
                                                   ui=kwargs.get('ui', {}),
                                                   config=self.config))

        cookie_rewriter = None
        if self.cookie_tracker and cookie_key:
            # skip add cookie if service worker is not 200
            # it seems cookie headers from service workers are not applied, so don't update in cache
            if wb_url.mod == 'sw_':
                cookie_key = None

            cookie_rewriter = self.cookie_tracker.get_rewriter(urlrewriter,
                                                               cookie_key)

        urlrewriter.rewrite_opts['ua_string'] = environ.get('HTTP_USER_AGENT')

        result = content_rw(record, urlrewriter, cookie_rewriter, head_insert_func, cdx, environ)

        status_headers, gen, is_rw = result

        if history_page:
            title = DefaultRewriter._extract_title(gen)
            if not title:
                title = unquote(environ.get('HTTP_X_WOMBAT_HISTORY_TITLE', ''))

            if not title:
                title = history_page

            self._add_history_page(cdx, kwargs, title)
            return WbResponse.json_response({'title': title})

        if setcookie_headers:
            status_headers.headers.extend(setcookie_headers)

        if ' ' not in status_headers.statusline:
            status_headers.statusline += ' None'

        if not is_ajax and self.enable_memento:
            self._add_memento_links(cdx['url'], full_prefix,
                                    memento_dt, cdx['timestamp'], status_headers,
                                    is_timegate, is_proxy, cdx.get('source-coll'),
                                    mod=pref_mod, pref_applied=pref_applied)

            set_content_loc = True

        if set_content_loc and not redirect_to_exact and not is_proxy:
            status_headers.headers.append(('Content-Location', urlrewriter.get_new_url(timestamp=cdx['timestamp'],
                                                                                       url=cdx['url'])))

        if not is_proxy:
            self.add_csp_header(wb_url, status_headers)

        response = WbResponse(status_headers, gen)

        if is_proxy and environ.get('HTTP_ORIGIN'):
            response.add_access_control_headers(environ)

        if r.status_code == 200 and kwargs.get('cache') == 'always' and environ.get('HTTP_REFERER'):
            response.status_headers['Cache-Control'] = 'public, max-age=31536000, immutable'

        return response

    def format_response(self, response, wb_url, full_prefix, is_timegate, is_proxy, timegate_closest_ts=None):
        memento_ts = None
        if not isinstance(response, WbResponse):
            content_type = 'text/html'

            # if not replay outer frame, specify utf-8 charset
            if not self.is_framed_replay(wb_url):
                content_type += '; charset=utf-8'
            else:
                memento_ts = timegate_closest_ts or wb_url.timestamp

            response = WbResponse.text_response(response, content_type=content_type)

        if self.enable_memento and response.status_headers.statusline.startswith('200'):
            self._add_memento_links(wb_url.url, full_prefix, None, memento_ts,
                                    response.status_headers, is_timegate, is_proxy, is_memento=not is_timegate)
        return response

    def _add_memento_links(self, url, full_prefix, memento_dt, memento_ts,
                           status_headers, is_timegate, is_proxy, coll=None,
                           pref_applied=None, mod=None, is_memento=True):
        """Adds the memento link headers to supplied StatusAndHeaders instance

        :param str url: The URI-R being rewritten
        :param str full_prefix: The replay prefix
        :param str|None memento_dt: The memento datetime for the URI-R being rewritten
        :param str memento_ts: The memento timestamp
        :param warcio.StatusAndHeaders status_headers:
        :param bool is_timegate: Are we returning a response for a timegate
        :param bool is_proxy: Are we operating in proxy mode
        :param str|None coll: The collection the URI-R is from
        :param str|None pref_applied:
        :param str|None mod: The rewrite modifier
        :param bool is_memento:
        :rtype: None
        """

        replay_mod = mod or self.replay_mod

        # memento url + header
        if not memento_dt and memento_ts:
            memento_dt = timestamp_to_http_date(memento_ts)

        if memento_dt:
            if is_memento:
                status_headers.headers.append(('Memento-Datetime', memento_dt))

            if is_proxy:
                memento_url = url
            else:
                memento_url = full_prefix + memento_ts + replay_mod
                memento_url += '/' + url
        else:
            memento_url = None

        timegate_url, timemap_url = self._get_timegate_timemap(url, full_prefix, mod)

        link = []
        if not is_proxy:
            link.append(MementoUtils.make_link(url, 'original'))
            link.append(MementoUtils.make_link(timegate_url, 'timegate'))
            link.append(MementoUtils.make_link(timemap_url, 'timemap'))

        if memento_dt:
            link.append(MementoUtils.make_memento_link(memento_url, 'memento', memento_dt, coll))

        link_str = ', '.join(link)

        status_headers.headers.append(('Link', link_str))

        vary = ''
        if is_timegate:
            vary = 'accept-datetime'

        if pref_applied:
            vary = 'Prefer' if not vary else vary + ', Prefer'
            status_headers.headers.append(('Preference-Applied', pref_applied))

        if vary:
            status_headers.headers.append(('Vary', vary))

    def _get_timegate_timemap(self, url, full_prefix, mod):
        # timegate url
        timegate_url = full_prefix
        mod = ''
        if mod:
            timegate_url += mod + '/'

        timegate_url += url

        # timemap url
        timemap_url = full_prefix + 'timemap/link/' + url
        return timegate_url, timemap_url

    def get_top_url(self, full_prefix, wb_url, cdx, kwargs):
        top_url = full_prefix + wb_url.to_str(mod='')
        return top_url

    def handle_error(self, environ, wbe):
        if isinstance(wbe, NotFoundException):
            return self._not_found_response(environ, wbe.url)
        else:
            return self._error_response(environ, wbe)

    def _not_found_response(self, environ, url):
        resp = self.not_found_view.render_to_string(environ, url=url, err_msg="Not Found")

        return WbResponse.text_response(resp, status='404 Not Found', content_type='text/html')

    def _error_response(self, environ, wbe):
        status = wbe.status()

        resp = self.error_view.render_to_string(environ,
                                                err_msg=wbe.url,
                                                err_details=wbe.msg,
                                                err_status=wbe.status_code)

        return WbResponse.text_response(resp, status=status, content_type='text/html')

    def _do_req(self, inputreq, wb_url, kwargs, skip_record):
        req_data = inputreq.reconstruct_request(wb_url.url)

        headers = {'Content-Length': str(len(req_data)),
                   'Content-Type': 'application/request'}

        headers.update(inputreq.warcserver_headers)

        if skip_record:
            headers['Recorder-Skip'] = '1'

        if wb_url.is_latest_replay():
            closest = 'now'
        else:
            closest = wb_url.timestamp

        params = {'url': wb_url.url, 'closest': closest, 'matchType': 'exact'}

        if wb_url.mod == 'vi_':
            params['content_type'] = self.VIDEO_INFO_CONTENT_TYPE

        upstream_url = self.get_upstream_url(wb_url, kwargs, params)

        r = requests.post(upstream_url,
                          data=BytesIO(req_data),
                          headers=headers,
                          stream=True)

        return r

    def do_query(self, wb_url, kwargs):
        """Performs the timemap query request for the supplied WbUrl
        returning the response

        :param WbUrl wb_url: The WbUrl to be queried
        :param dict kwargs: Optional keyword arguments
        :return: The queries response
        :rtype: requests.Response
        """
        params = {
            'url': wb_url.url,
            'output': kwargs.get('output', 'json'),
            'from': wb_url.timestamp,
            'to': wb_url.end_timestamp
        }
        if 'memento_format' in kwargs:
            params['memento_format'] = kwargs['memento_format']

        if 'limit' in kwargs:
            params['limit'] = kwargs['limit']

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
                timegate, timemap = self._get_timegate_timemap(wb_url.url, full_prefix, wb_url.mod)

                text = MementoUtils.wrap_timemap_header(wb_url.url,
                                                        timegate,
                                                        timemap,
                                                        res.text)
        return WbResponse.text_response(text,
                                        content_type=content_type,
                                        status=status)

    def handle_timemap(self, wb_url, kwargs, full_prefix):
        output = kwargs.get('output')
        kwargs['memento_format'] = full_prefix + '{timestamp}' + self.replay_mod + '/{url}'
        res = self.do_query(wb_url, kwargs)
        return self.make_timemap(wb_url, res, full_prefix, output)

    def handle_query(self, environ, wb_url, kwargs, full_prefix):
        prefix = self.get_full_prefix(environ)

        res = dict(parse_qsl(environ.get("QUERY_STRING")))
        is_advanced = res.get("matchType", "exact") != "exact" or res.get("url", "").endswith("*")

        # vue ui not supported for advanced search for now
        ui = kwargs.get("ui", {})
        if is_advanced:
            ui["vue_calendar_ui"] = False

        params = dict(url=wb_url.url,
                      prefix=prefix,
                      ui=ui)

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
        # return request.script_name
        return environ.get('SCRIPT_NAME', '') + '/'

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


        # additional checks for proxy mode only
        if not ('wsgiprox.proxy_host' in environ):
            return False

        # if Chrome Sec-Fetch-Mode is set and is set to 'cors', then
        # a fetch / ajax request
        sec_fetch_mode = environ.get('HTTP_SEC_FETCH_MODE')
        if sec_fetch_mode and sec_fetch_mode == 'cors':
            return True

        return False

    def is_preflight(self, environ):
        if environ.get('REQUEST_METHOD') != 'OPTIONS':
            return False

        if not environ.get('HTTP_ORIGIN'):
            return False

        if not environ.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD') and not environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS'):
            return False

        return True


    def get_base_url(self, wb_url, kwargs):
        type_ = kwargs.get('type')
        return self.paths[type_].format(**kwargs)

    def get_upstream_url(self, wb_url, kwargs, params):
        base_url = self.get_base_url(wb_url, kwargs)
        param_str = urlencode(params, True)
        if param_str:
            q_char = '&' if '?' in base_url else '?'
            base_url += q_char + param_str
        return base_url

    def get_cookie_key(self, kwargs):
        # note: currently this is per-collection, so enabled only for live or recording
        # to support multiple users recording/live, would need per user cookie
        if kwargs.get('index') == '$live' or kwargs.get('type') == 'record':
            return 'cookie:' + kwargs['coll']
        else:
            return None

    def _add_history_page(self, cdx, kwargs, doc_title):
        pass

    def _add_custom_params(self, cdx, headers, kwargs, record):
        pass

    def get_top_frame_params(self, wb_url, kwargs):
        return {'metadata': kwargs.get('metadata', {}),
                'ui': kwargs.get('ui', {})
               }

    def handle_custom_response(self, environ, wb_url, full_prefix, host_prefix, kwargs):
        if self.is_framed_replay(wb_url):
            extra_params = self.get_top_frame_params(wb_url, kwargs)
            return self.frame_insert_view.get_top_frame(wb_url,
                                                        full_prefix,
                                                        host_prefix,
                                                        environ,
                                                        self.frame_mod,
                                                        self.replay_mod,
                                                        self.client_side_replay,
                                                        coll='',
                                                        extra_params=extra_params)

        return None
