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

from pywb.utils.bufferedreaders import BufferedReader

from certauth import CertificateAuthority


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


#=================================================================
class BaseCollResolver(object):
    def __init__(self, routes, config):
        self.routes = routes
        self.pre_connect = config.get('pre_connect', False)
        self.use_default_coll = config.get('use_default_coll', True)

    def resolve(self, env):
        route = None
        coll = None
        matcher = None

        proxy_coll = self.get_proxy_coll(env)

        # invalid parsing
        if proxy_coll == '':
            return None, None, None, self.select_coll_response(env)

        if proxy_coll is None and isinstance(self.use_default_coll, str):
            proxy_coll = self.use_default_coll

        if proxy_coll:
            proxy_coll = '/' + proxy_coll + '/'

            for r in self.routes:
                matcher, c = r.is_handling(proxy_coll)
                if matcher:
                    route = r
                    coll = c
                    break

            # if no match, return coll selection response
            if not route:
                return None, None, None, self.select_coll_response(env)

        # if 'use_default_coll'
        elif self.use_default_coll == True or len(self.routes) == 1:
            route = self.routes[0]
            coll = self.routes[0].path

        # otherwise, return the appropriate coll selection response
        else:
            return None, None, None, self.select_coll_response(env)

        return route, coll, matcher, None


#=================================================================
class ProxyAuthResolver(BaseCollResolver):
    DEFAULT_MSG = 'Please enter name of a collection to use with proxy mode'

    def __init__(self, routes, config):
        config['pre_connect'] = True
        super(ProxyAuthResolver, self).__init__(routes, config)
        self.auth_msg = config.get('auth_msg', self.DEFAULT_MSG)

    def get_proxy_coll(self, env):
        proxy_auth = env.get('HTTP_PROXY_AUTHORIZATION')

        if not proxy_auth:
            return None

        proxy_coll = self.read_basic_auth_coll(proxy_auth)
        return proxy_coll

    def select_coll_response(self, env):
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


#=================================================================
class CookieResolver(BaseCollResolver):
    def __init__(self, routes, config):
        config['pre_connect'] = False
        super(CookieResolver, self).__init__(routes, config)
        self.magic_name = config.get('magic_name', 'pywb-proxy.com')
        self.cookie_name = config.get('cookie_name', '__pywb_coll')
        self.proxy_select_view = config.get('proxy_select_view')

    def get_proxy_coll(self, env):
        cookie = self.extract_client_cookie(env, self.cookie_name)
        return cookie

    def select_coll_response(self, env):
        return self.make_magic_response('auto',
                                        env['REL_REQUEST_URI'],
                                        env)

    def resolve(self, env):
        url = env['REL_REQUEST_URI']

        if ('.' + self.magic_name) in url:
            return None, None, None, self.handle_magic_page(url, env)

        return super(CookieResolver, self).resolve(env)

    def handle_magic_page(self, url, env):
        parts = urlparse.urlsplit(url)

        path_url = parts.path[1:]
        if parts.query:
            path_url += '?' + parts.query

        if parts.netloc.startswith('auto'):
            coll = self.extract_client_cookie(env, self.cookie_name)

            if coll:
                return self.make_sethost_cookie_response(coll, path_url, env)
            else:
                return self.make_magic_response('select', path_url, env)

        elif '.set.' in parts.netloc:
            coll = parts.netloc.split('.', 1)[0]
            headers = self.make_cookie_headers(coll, self.magic_name)

            return self.make_sethost_cookie_response(coll, path_url, env,
                                                     headers=headers)

        elif '.sethost.' in parts.netloc:
            host_parts = parts.netloc.split('.', 1)
            coll = host_parts[0]

            inx = parts.netloc.find('.' + self.magic_name + '.')
            domain = parts.netloc[inx + len(self.magic_name) + 2:]

            headers = self.make_cookie_headers(coll, domain)

            full_url = env['pywb.proxy_scheme'] + '://' + domain
            full_url += '/' + path_url
            return WbResponse.redir_response(full_url, headers=headers)

        elif self.proxy_select_view:
            route_temp = env['pywb.proxy_scheme'] + '://%s.set.'
            route_temp += self.magic_name + '/' + path_url

            return (self.proxy_select_view.
                    render_response(routes=self.routes,
                                    route_temp=route_temp,
                                    url=path_url))
        else:
            return WbResponse.text_response('select text for ' + path_url)

    def make_cookie_headers(self, coll, domain):
        cookie_val = '{0}={1}; Path=/; Domain=.{2}; HttpOnly'
        cookie_val = cookie_val.format(self.cookie_name, coll, domain)
        headers = [('Set-Cookie', cookie_val)]
        return headers

    def make_sethost_cookie_response(self, coll, path_url, env, headers=None):
        path_parts = urlparse.urlsplit(path_url)

        new_url = path_parts.path[1:]
        if path_parts.query:
            new_url += '?' + path_parts.query

        return self.make_magic_response(coll + '.sethost', new_url, env,
                                        suffix=path_parts.netloc,
                                        headers=headers)


    def make_magic_response(self, prefix, url, env,
                            suffix=None, headers=None):
        full_url = env['pywb.proxy_scheme'] + '://' + prefix + '.'
        full_url += self.magic_name
        if suffix:
            full_url += '.' + suffix
        full_url += '/' + url
        return WbResponse.redir_response(full_url, headers=headers)

    @staticmethod
    def extract_client_cookie(env, cookie_name):
        cookie_header = env.get('HTTP_COOKIE')
        if not cookie_header:
            return None

        # attempt to extract cookie_name only
        inx = cookie_header.find(cookie_name)
        if inx < 0:
            return None

        end_inx = cookie_header.find(';', inx)
        if end_inx > 0:
            value = cookie_header[inx:end_inx]
        else:
            value = cookie_header[inx:]

        value = value.split('=')
        if len(value) < 2:
            return None

        value = value[1].strip()
        return value

