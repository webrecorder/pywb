from wbrequestresponse import WbResponse, WbRequest
from archivalrouter import ArchivalRouter

import urlparse
import base64

import socket
import ssl

from pywb.rewrite.url_rewriter import HttpsUrlRewriter
from pywb.utils.wbexception import BadRequestException

from pywb.utils.bufferedreaders import BufferedReader

from certauth import CertificateAuthority

from proxy_resolvers import ProxyAuthResolver


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

    PAC_PATH = '/proxy.pac'
    BLOCK_SIZE = 4096

    def __init__(self, routes, **kwargs):
        self.hostpaths = kwargs.get('hostpaths')

        self.error_view = kwargs.get('error_view')

        proxy_options = kwargs.get('config', {})
        if proxy_options:
            proxy_options = proxy_options.get('proxy_options', {})

        self.resolver = ProxyAuthResolver(routes, proxy_options)
        #self.resolver = CookieResolver(routes, proxy_options)

        self.unaltered = proxy_options.get('unaltered_replay', False)

        self.proxy_pac_path = proxy_options.get('pac_path', self.PAC_PATH)


        if proxy_options.get('enable_https_proxy'):
            ca_file = proxy_options.get('root_ca_file')

            # attempt to create the root_ca_file if doesn't exist
            # (generally recommended to create this seperately)
            certname = proxy_options.get('root_ca_name')
            CertificateAuthority.generate_ca_root(certname, ca_file)

            certs_dir = proxy_options.get('certs_dir')
            self.ca = CertificateAuthority(ca_file=ca_file,
                                           certs_dir=certs_dir)
        else:
            self.ca = None

    def __call__(self, env):
        is_https = (env['REQUEST_METHOD'] == 'CONNECT')

        # for non-https requests, check pac path and non-proxy urls
        if not is_https:
            url = env['REL_REQUEST_URI']

            if url == self.proxy_pac_path:
                return self.make_pac_response(env)

            if not url.startswith(('http://', 'https://')):
                return None

        env['pywb.proxy_scheme'] = 'https' if is_https else 'http'

        # check resolver, for pre connect resolve
        if self.resolver.pre_connect:
            route, coll, matcher, response = self.resolver.resolve(env)
            if response:
                return response

        # do connect, then get updated url
        if is_https:
            response = self.handle_connect(env)
            if response:
                return response

            url = env['REL_REQUEST_URI']

        # check resolver, post connect
        if not self.resolver.pre_connect:
            route, coll, matcher, response = self.resolver.resolve(env)
            if response:
                return response

        wbrequest = route.request_class(env,
                              request_uri=url,
                              wb_url_str=url,
                              coll=coll,
                              host_prefix=self.hostpaths[0],
                              wburl_class=route.handler.get_wburl_type(),
                              urlrewriter_class=HttpsUrlRewriter,
                              use_abs_prefix=False,
                              is_proxy=True)

        if matcher:
            route.apply_filters(wbrequest, matcher)

        if self.unaltered:
            wbrequest.wb_url.mod = 'id_'

        return route.handler(wbrequest)

    def get_request_socket(self, env):
        if not self.ca:
            return None

        sock = None

        if env.get('uwsgi.version'):
            try:
                import uwsgi
                fd = uwsgi.connection_fd()
                conn = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
                sock = socket.socket(_sock=conn)
            except Exception:
                pass
        elif env.get('gunicorn.socket'):
            sock = env['gunicorn.socket']

        if not sock:
            # attempt to find socket from wsgi.input
            input_ = env.get('wsgi.input')
            if input_ and hasattr(input_, '_sock'):
                sock = socket.socket(_sock=input_._sock)

        return sock

    def handle_connect(self, env):
        sock = self.get_request_socket(env)
        if not sock:
            return WbResponse.text_response('HTTPS Proxy Not Supported',
                                            '405 HTTPS Proxy Not Supported')

        sock.send('HTTP/1.0 200 Connection Established\r\n')
        sock.send('Server: pywb proxy\r\n')
        sock.send('\r\n')

        hostname, port = env['REL_REQUEST_URI'].split(':')
        created, certfile = self.ca.get_cert_for_host(hostname)

        ssl_sock = ssl.wrap_socket(sock,
                                   server_side=True,
                                   certfile=certfile,
                                   ciphers="ALL",
                                   ssl_version=ssl.PROTOCOL_SSLv23)

        env['pywb.proxy_ssl_sock'] = ssl_sock

        buffreader = BufferedReader(ssl_sock, block_size=self.BLOCK_SIZE)

        statusline = buffreader.readline()
        statusparts = statusline.split(' ')

        if len(statusparts) < 3:
            raise BadRequestException('Invalid Proxy Request')

        env['REQUEST_METHOD'] = statusparts[0]
        env['REL_REQUEST_URI'] = ('https://' +
                                  env['REL_REQUEST_URI'].replace(':443', '') +
                                  statusparts[1])

        env['SERVER_PROTOCOL'] = statusparts[2].strip()

        env['SERVER_NAME'] = hostname
        env['SERVER_PORT'] = port

        queryparts = env['REL_REQUEST_URI'].split('?', 1)
        env['PATH_INFO'] = queryparts[0]
        env['QUERY_STRING'] = queryparts[1] if len(queryparts) > 1 else ''

        env['wsgi.url_scheme'] = 'https'

        while True:
            line = buffreader.readline()
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

            if not name in ('CONTENT_LENGTH', 'CONTENT_TYPE'):
                name = 'HTTP_' + name

            env[name] = value

        remain = buffreader.rem_length()
        if remain > 0:
            remainder = buffreader.read(self.BLOCK_SIZE)
            input_ = socket._fileobject(ssl_sock, mode='r')
            env['wsgi.input'] = BufferedReader(input_,
                                               block_size=self.BLOCK_SIZE,
                                               starting_data=remainder)

    # Proxy Auto-Config (PAC) script for the proxy
    def make_pac_response(self, env):
        import os
        hostname = os.environ.get('PYWB_HOST_NAME')
        if not hostname:
            server_hostport = env['SERVER_NAME'] + ':' + env['SERVER_PORT']
            hostonly = env['SERVER_NAME']
        else:
            server_hostport = hostname
            hostonly = hostname.split(':')[0]

        buff = 'function FindProxyForURL (url, host) {\n'

        direct = '    if (shExpMatch(host, "{0}")) {{ return "DIRECT"; }}\n'

        for hostpath in self.hostpaths:
            parts = urlparse.urlsplit(hostpath).netloc.split(':')
            buff += direct.format(parts[0])

        buff += direct.format(hostonly)

        #buff += '\n    return "PROXY {0}";\n}}\n'.format(self.hostpaths[0])
        buff += '\n    return "PROXY {0}";\n}}\n'.format(server_hostport)

        content_type = 'application/x-ns-proxy-autoconfig'

        return WbResponse.text_response(buff, content_type=content_type)
