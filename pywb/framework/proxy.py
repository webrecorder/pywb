from wbrequestresponse import WbResponse, WbRequest
from archivalrouter import ArchivalRouter

import urlparse
import base64

import socket
import ssl
from io import BytesIO

from pywb.rewrite.url_rewriter import HttpsUrlRewriter
from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.wbexception import BadRequestException

from certa import CertificateAuthority


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

    def __init__(self, routes, **kwargs):
        self.routes = routes
        self.hostpaths = kwargs.get('hostpaths')

        self.error_view = kwargs.get('error_view')

        proxy_options = kwargs.get('config', {})
        if proxy_options:
            proxy_options = proxy_options.get('proxy_options', {})

        self.auth_msg = proxy_options.get('auth_msg',
        'Please enter name of a collection to use for proxy mode')

        self.use_default_coll = proxy_options.get('use_default_coll', True)

        self.unaltered = proxy_options.get('unaltered_replay', False)

        self.ca = CertificateAuthority()


    def __call__(self, env):
        is_https = (env['REQUEST_METHOD'] == 'CONNECT')

        if not is_https:
            url = env['REL_REQUEST_URI']

            if url.endswith('/proxy.pac'):
                return self.make_pac_response(env)

            if not url.startswith(('http://', 'https://')):
                return None

        proxy_auth = env.get('HTTP_PROXY_AUTHORIZATION')

        route = None
        coll = None
        matcher = None

        if proxy_auth:
            proxy_coll = self.read_basic_auth_coll(proxy_auth)

            if not proxy_coll:
                return self.proxy_auth_coll_response()

            proxy_coll = '/' + proxy_coll + '/'

            for r in self.routes:
                matcher, c = r.is_handling(proxy_coll)
                if matcher:
                    route = r
                    coll = c
                    break

            if not route:
                return self.proxy_auth_coll_response()

        # if 'use_default_coll' or only one collection, use that
        # for proxy mode
        elif self.use_default_coll or len(self.routes) == 1:
            route = self.routes[0]
            coll = self.routes[0].regex.pattern

        # otherwise, require proxy auth 407 to select collection
        else:
            return self.proxy_auth_coll_response()

        # do connect, then get updated url
        if is_https:
            self.handle_connect(env)

            url = env['REL_REQUEST_URI']

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
        if env.get('uwsgi.version'):
            import uwsgi
            fd = uwsgi.connection_fd()
            conn = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
            sock = socket.socket(_sock=conn)
        elif env.get('gunicorn.socket'):
            sock = env['gunicorn.socket']
        else:
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

        hostname = env['REL_REQUEST_URI'].split(':')[0]

        ssl_sock = ssl.wrap_socket(sock, server_side=True,
                                   certfile=self.ca[hostname])
                                   #ssl_version=ssl.PROTOCOL_SSLv23)

        env['pywb.proxy_ssl_sock'] = ssl_sock

        #todo: better reading of all headers
        buff = ssl_sock.recv(4096)

        buffreader = BytesIO(buff)

        statusline = buffreader.readline()
        statusparts = statusline.split(' ')

        if len(statusparts) < 3:
            raise BadRequestException('Invalid Proxy Request')

        env['REQUEST_METHOD'] = statusparts[0]
        env['REL_REQUEST_URI'] = ('https://' +
                                  env['REL_REQUEST_URI'].replace(':443', '') +
                                  statusparts[1])

        env['SERVER_PROTOCOL'] = statusparts[2].strip()

        queryparts = env['REL_REQUEST_URI'].split('?', 1)
        env['PATH_INFO'] = queryparts[0]
        env['QUERY_STRING'] = queryparts[1] if len(queryparts) > 1 else ''

        env['wsgi.input'] = socket._fileobject(ssl_sock, mode='r')

        while True:
            line = buffreader.readline()
            if not line:
                break

            parts = line.split(':')
            if len(parts) < 2:
                continue

            name = 'HTTP_' + parts[0].replace('-', '_').upper()
            env[name] = parts[1]

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

    def proxy_auth_coll_response(self):
        proxy_msg = 'Basic realm="{0}"'.format(self.auth_msg)

        headers = [('Content-Type', 'text/plain'),
                   ('Proxy-Authenticate', proxy_msg)]

        status_headers = StatusAndHeaders('407 Proxy Authentication', headers)

        value = self.auth_msg

        return WbResponse(status_headers, value=[value])

    @staticmethod
    def read_basic_auth_coll(value):
        parts = value.split(' ')
        if parts[0].lower() != 'basic':
            return ''

        if len(parts) != 2:
            return ''

        user_pass = base64.b64decode(parts[1])
        return user_pass.split(':')[0]
