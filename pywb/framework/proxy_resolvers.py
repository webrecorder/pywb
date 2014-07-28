from wbrequestresponse import WbResponse, WbRequest
from pywb.utils.statusandheaders import StatusAndHeaders
import urlparse
import base64


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
# Experimental CookieResolver
class CookieResolver(BaseCollResolver):  # pragma: no cover
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
