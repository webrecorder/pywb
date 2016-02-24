from __future__ import absolute_import

from pywb.framework.wbrequestresponse import WbResponse, WbRequest
from pywb.framework.archivalrouter import ArchivalRouter

from six.moves.urllib.parse import urlsplit
import base64

import socket
import ssl

from io import BytesIO

from pywb.rewrite.url_rewriter import SchemeOnlyUrlRewriter, UrlRewriter
from pywb.rewrite.rewrite_content import RewriteContent
from pywb.utils.wbexception import BadRequestException

from pywb.utils.bufferedreaders import BufferedReader
from pywb.utils.loaders import to_native_str

from pywb.framework.proxy_resolvers import ProxyAuthResolver, CookieResolver, IPCacheResolver

from tempfile import SpooledTemporaryFile


#=================================================================
class ProxyArchivalRouter(ArchivalRouter):
    """
    A router which combines both archival and proxy modes support
    First, request is treated as a proxy request using ProxyRouter
    Second, if not handled by the router, it is treated as a regular
    archival mode request.
    """
    def __init__(self, routes, **kwargs):
        super(ProxyArchivalRouter, self).__init__(routes, **kwargs)
        self.proxy = ProxyRouter(routes, **kwargs)

    def __call__(self, env):
        response = self.proxy(env)
        if response:
            return response

        response = super(ProxyArchivalRouter, self).__call__(env)
        if response:
            return response


#=================================================================
class ProxyRouter(object):
    """
    A router which supports http proxy mode requests
    Handles requests of the form: GET http://example.com

    The router returns latest capture by default.
    However, if Memento protocol support is enabled,
    the memento Accept-Datetime header can be used
    to select specific capture.
    See: http://www.mementoweb.org/guide/rfc/#Pattern1.3
    for more details.
    """

    BLOCK_SIZE = 4096
    DEF_MAGIC_NAME = 'pywb.proxy'
    BUFF_RESPONSE_MEM_SIZE = 1024*1024

    CERT_DL_PEM = '/pywb-ca.pem'
    CERT_DL_P12 = '/pywb-ca.p12'

    CA_ROOT_FILE = './ca/pywb-ca.pem'
    CA_ROOT_NAME = 'pywb https proxy replay CA'
    CA_CERTS_DIR = './ca/certs/'

    EXTRA_HEADERS = {'cache-control': 'no-cache',
                     'connection': 'close',
                     'p3p': 'CP="NOI ADM DEV COM NAV OUR STP"'}

    def __init__(self, routes, **kwargs):
        self.error_view = kwargs.get('error_view')

        proxy_options = kwargs.get('config', {})
        if proxy_options:
            proxy_options = proxy_options.get('proxy_options', {})

        self.magic_name = proxy_options.get('magic_name')
        if not self.magic_name:
            self.magic_name = self.DEF_MAGIC_NAME
            proxy_options['magic_name'] = self.magic_name

        self.extra_headers = proxy_options.get('extra_headers')
        if not self.extra_headers:
            self.extra_headers = self.EXTRA_HEADERS
            proxy_options['extra_headers'] = self.extra_headers

        res_type = proxy_options.get('cookie_resolver', True)
        if res_type == 'auth' or not res_type:
            self.resolver = ProxyAuthResolver(routes, proxy_options)
        elif res_type == 'ip':
            self.resolver = IPCacheResolver(routes, proxy_options)
        #elif res_type == True or res_type == 'cookie':
        #    self.resolver = CookieResolver(routes, proxy_options)
        else:
            self.resolver = CookieResolver(routes, proxy_options)

        self.use_banner = proxy_options.get('use_banner', True)
        self.use_wombat = proxy_options.get('use_client_rewrite', True)

        self.proxy_cert_dl_view = proxy_options.get('proxy_cert_download_view')

        if not proxy_options.get('enable_https_proxy'):
            self.ca = None
            return

        try:
            from certauth.certauth import CertificateAuthority
        except ImportError:  #pragma: no cover
            print('HTTPS proxy is not available as the "certauth" module ' +
                  'is not installed')
            print('Please install via "pip install certauth" ' +
                  'to enable HTTPS support')
            self.ca = None
            return

        # HTTPS Only Options
        ca_file = proxy_options.get('root_ca_file', self.CA_ROOT_FILE)

        # attempt to create the root_ca_file if doesn't exist
        # (generally recommended to create this seperately)
        ca_name = proxy_options.get('root_ca_name', self.CA_ROOT_NAME)

        certs_dir = proxy_options.get('certs_dir', self.CA_CERTS_DIR)
        self.ca = CertificateAuthority(ca_file=ca_file,
                                       certs_dir=certs_dir,
                                       ca_name=ca_name)

        self.use_wildcard = proxy_options.get('use_wildcard_certs', True)

    def __call__(self, env):
        is_https = (env['REQUEST_METHOD'] == 'CONNECT')
        ArchivalRouter.ensure_rel_uri_set(env)

        # for non-https requests, check non-proxy urls
        if not is_https:
            url = env['REL_REQUEST_URI']

            if not url.startswith(('http://', 'https://')):
                return None

            env['pywb.proxy_scheme'] = 'http'

        route = None
        coll = None
        matcher = None
        response = None
        ts = None

        # check resolver, for pre connect resolve
        if self.resolver.pre_connect:
            route, coll, matcher, ts, response = self.resolver.resolve(env)
            if response:
                return response

        # do connect, then get updated url
        if is_https:
            response = self.handle_connect(env)
            if response:
                return response

            url = env['REL_REQUEST_URI']
        else:
            parts = urlsplit(env['REL_REQUEST_URI'])
            hostport = parts.netloc.split(':', 1)
            env['pywb.proxy_host'] = hostport[0]
            env['pywb.proxy_port'] = hostport[1] if len(hostport) == 2 else ''
            env['pywb.proxy_req_uri'] = parts.path
            if parts.query:
                env['pywb.proxy_req_uri'] += '?' + parts.query
                env['pywb.proxy_query'] = parts.query

        if self.resolver.supports_switching:
            env['pywb_proxy_magic'] = self.magic_name

        # route (static) and other resources to archival replay
        if env['pywb.proxy_host'] == self.magic_name:
            env['REL_REQUEST_URI'] = env['pywb.proxy_req_uri']

            # special case for proxy install
            response = self.handle_cert_install(env)
            if response:
                return response

            return None

        # check resolver, post connect
        if not self.resolver.pre_connect:
            route, coll, matcher, ts, response = self.resolver.resolve(env)
            if response:
                return response

        rel_prefix = ''

        custom_prefix = env.get('HTTP_PYWB_REWRITE_PREFIX', '')
        if custom_prefix:
            host_prefix = custom_prefix
            urlrewriter_class = UrlRewriter
            abs_prefix = True
            # always rewrite to absolute here
            rewrite_opts = dict(no_match_rel=True)
        else:
            host_prefix = env['pywb.proxy_scheme'] + '://' + self.magic_name
            urlrewriter_class = SchemeOnlyUrlRewriter
            abs_prefix = False
            rewrite_opts = {}

        # special case for proxy calendar
        if (env['pywb.proxy_host'] == 'query.' + self.magic_name):
            url = env['pywb.proxy_req_uri'][1:]
            rel_prefix = '/'

        if ts is not None:
            url = ts + '/' + url

        wbrequest = route.request_class(env,
                              request_uri=url,
                              wb_url_str=url,
                              coll=coll,
                              host_prefix=host_prefix,
                              rel_prefix=rel_prefix,
                              wburl_class=route.handler.get_wburl_type(),
                              urlrewriter_class=urlrewriter_class,
                              use_abs_prefix=abs_prefix,
                              rewrite_opts=rewrite_opts,
                              is_proxy=True)

        if matcher:
            route.apply_filters(wbrequest, matcher)

        # full rewrite and banner
        if self.use_wombat and self.use_banner:
            wbrequest.wb_url.mod = ''
        elif self.use_banner:
        # banner only, no rewrite
            wbrequest.wb_url.mod = 'bn_'
        else:
        # unaltered, no rewrite or banner
            wbrequest.wb_url.mod = 'uo_'

        response = route.handler(wbrequest)
        if not response:
            return None

        # add extra headers for replay responses
        if wbrequest.wb_url and wbrequest.wb_url.is_replay():
            response.status_headers.replace_headers(self.extra_headers)

        # check for content-length
        res = response.status_headers.get_header('content-length')
        try:
            if int(res) > 0:
                return response
        except:
            pass

        # need to either chunk or buffer to get content-length
        if env.get('SERVER_PROTOCOL') == 'HTTP/1.1':
            response.status_headers.remove_header('content-length')
            response.status_headers.headers.append(('Transfer-Encoding', 'chunked'))
            response.body = self._chunk_encode(response.body)
        else:
            response.body = self._buffer_response(response.status_headers,
                                                  response.body)

        return response

    @staticmethod
    def _chunk_encode(orig_iter):
        for chunk in orig_iter:
            if not len(chunk):
                continue
            chunk_len = b'%X\r\n' % len(chunk)
            yield chunk_len
            yield chunk
            yield b'\r\n'

        yield b'0\r\n\r\n'

    @staticmethod
    def _buffer_response(status_headers, iterator):
        out = SpooledTemporaryFile(ProxyRouter.BUFF_RESPONSE_MEM_SIZE)
        size = 0

        for buff in iterator:
            size += len(buff)
            out.write(buff)

        content_length_str = str(size)
        # remove existing content length
        status_headers.replace_header('Content-Length',
                                      content_length_str)

        out.seek(0)
        return RewriteContent.stream_to_gen(out)

    def get_request_socket(self, env):
        if not self.ca:
            return None

        sock = None

        if env.get('uwsgi.version'):  # pragma: no cover
            try:
                import uwsgi
                fd = uwsgi.connection_fd()
                conn = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock = socket.socket(_sock=conn)
                except:
                    sock = conn
            except Exception as e:
                pass
        elif env.get('gunicorn.socket'):  # pragma: no cover
            sock = env['gunicorn.socket']

        if not sock:
            # attempt to find socket from wsgi.input
            input_ = env.get('wsgi.input')
            if input_:
                if hasattr(input_, '_sock'):  # pragma: no cover
                    raw = input_._sock
                    sock = socket.socket(_sock=raw)  # pragma: no cover
                elif hasattr(input_, 'raw'):
                    sock = input_.raw._sock

        return sock

    def handle_connect(self, env):
        sock = self.get_request_socket(env)
        if not sock:
            return WbResponse.text_response('HTTPS Proxy Not Supported',
                                            '405 HTTPS Proxy Not Supported')

        sock.send(b'HTTP/1.0 200 Connection Established\r\n')
        sock.send(b'Proxy-Connection: close\r\n')
        sock.send(b'Server: pywb proxy\r\n')
        sock.send(b'\r\n')

        hostname, port = env['REL_REQUEST_URI'].split(':')

        if not self.use_wildcard:
            certfile = self.ca.cert_for_host(hostname)
        else:
            certfile = self.ca.get_wildcard_cert(hostname)

        try:
            ssl_sock = ssl.wrap_socket(sock,
                                       server_side=True,
                                       certfile=certfile,
                                       #ciphers="ALL",
                                       suppress_ragged_eofs=False,
                                       ssl_version=ssl.PROTOCOL_SSLv23
                                       )
            env['pywb.proxy_ssl_sock'] = ssl_sock

            buffreader = BufferedReader(ssl_sock, block_size=self.BLOCK_SIZE)

            statusline = to_native_str(buffreader.readline().rstrip())

        except Exception as se:
            raise BadRequestException(se.message)

        statusparts = statusline.split(' ')

        if len(statusparts) < 3:
            raise BadRequestException('Invalid Proxy Request: ' + statusline)

        env['REQUEST_METHOD'] = statusparts[0]
        env['REL_REQUEST_URI'] = ('https://' +
                                  env['REL_REQUEST_URI'].replace(':443', '') +
                                  statusparts[1])

        env['SERVER_PROTOCOL'] = statusparts[2].strip()

        env['pywb.proxy_scheme'] = 'https'

        env['pywb.proxy_host'] = hostname
        env['pywb.proxy_port'] = port
        env['pywb.proxy_req_uri'] = statusparts[1]

        queryparts = env['REL_REQUEST_URI'].split('?', 1)
        env['PATH_INFO'] = queryparts[0]
        env['QUERY_STRING'] = queryparts[1] if len(queryparts) > 1 else ''
        env['pywb.proxy_query'] = env['QUERY_STRING']

        while True:
            line = to_native_str(buffreader.readline())
            if line:
                line = line.rstrip()

            if not line:
                break

            parts = line.split(':', 1)
            if len(parts) < 2:
                continue

            name = parts[0].strip()
            value = parts[1].strip()

            name = name.replace('-', '_').upper()

            if name not in ('CONTENT_LENGTH', 'CONTENT_TYPE'):
                name = 'HTTP_' + name

            env[name] = value

        env['wsgi.input'] = buffreader
        #remain = buffreader.rem_length()
        #if remain > 0:
            #remainder = buffreader.read()
            #env['wsgi.input'] = BufferedReader(BytesIO(remainder))
            #remainder = buffreader.read(self.BLOCK_SIZE)
            #env['wsgi.input'] = BufferedReader(ssl_sock,
            #                                   block_size=self.BLOCK_SIZE,
            #                                   starting_data=remainder)

    def handle_cert_install(self, env):
        if env['pywb.proxy_req_uri'] in ('/', '/index.html', '/index.html'):
            available = (self.ca is not None)

            if self.proxy_cert_dl_view:
                return (self.proxy_cert_dl_view.
                         render_response(available=available,
                                         pem_path=self.CERT_DL_PEM,
                                         p12_path=self.CERT_DL_P12))

        elif env['pywb.proxy_req_uri'] == self.CERT_DL_PEM:
            if not self.ca:
                return None

            buff = b''
            with open(self.ca.ca_file, 'rb') as fh:
                buff = fh.read()

            content_type = 'application/x-x509-ca-cert'
            headers = [('Content-Length', str(len(buff)))]

            return WbResponse.bin_stream([buff],
                                         content_type=content_type,
                                         headers=headers)

        elif env['pywb.proxy_req_uri'] == self.CERT_DL_P12:
            if not self.ca:
                return None

            buff = self.ca.get_root_PKCS12()

            content_type = 'application/x-pkcs12'
            headers = [('Content-Length', str(len(buff)))]

            return WbResponse.bin_stream([buff],
                                         content_type=content_type,
                                         headers=headers)
