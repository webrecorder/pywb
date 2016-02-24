from pywb.framework.wbrequestresponse import WbResponse
from pywb.utils.loaders import extract_client_cookie
from pywb.utils.wbexception import WbException
from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.rewrite.wburl import WbUrl

from pywb.framework.cache import create_cache
from pywb.framework.basehandlers import WbUrlHandler

from six.moves.urllib.parse import parse_qs, urlsplit
import six

from pywb.utils.loaders import to_native_str

import base64
import os
import json


#=================================================================
class BaseCollResolver(object):
    def __init__(self, routes, config):
        self.routes = routes
        self.use_default_coll = config.get('use_default_coll')

    @property
    def pre_connect(self):
        return False

    def resolve(self, env):
        route = None
        coll = None
        matcher = None
        ts = None

        proxy_coll, ts = self.get_proxy_coll_ts(env)

        # invalid parsing
        if proxy_coll == '':
            return None, None, None, None, self.select_coll_response(env, proxy_coll)

        if proxy_coll is None and isinstance(self.use_default_coll, str):
            proxy_coll = self.use_default_coll

        if proxy_coll:
            path = '/' + proxy_coll + '/'

            for r in self.routes:
                matcher, c = r.is_handling(path)
                if matcher:
                    route = r
                    coll = c
                    break

            # if no match, return coll selection response
            if not route:
                return None, None, None, None, self.select_coll_response(env, proxy_coll)

        # if 'use_default_coll', find first WbUrl-handling collection
        elif self.use_default_coll:
            raise Exception('use_default_coll: true no longer supported, please specify collection name')
            #for route in self.routes:
            #    if isinstance(route.handler, WbUrlHandler):
            #        return route, route.path, matcher, ts, None

        # otherwise, return the appropriate coll selection response
        else:
            return None, None, None, None, self.select_coll_response(env, proxy_coll)

        return route, coll, matcher, ts, None


#=================================================================
class ProxyAuthResolver(BaseCollResolver):
    DEFAULT_MSG = 'Please enter name of a collection to use with proxy mode'

    def __init__(self, routes, config):
        super(ProxyAuthResolver, self).__init__(routes, config)
        self.auth_msg = config.get('auth_msg', self.DEFAULT_MSG)

    @property
    def pre_connect(self):
        return True

    @property
    def supports_switching(self):
        return False

    def get_proxy_coll_ts(self, env):
        proxy_auth = env.get('HTTP_PROXY_AUTHORIZATION')

        if not proxy_auth:
            return None, None

        proxy_coll = self.read_basic_auth_coll(proxy_auth)
        return proxy_coll, None

    def select_coll_response(self, env, default_coll=None):
        proxy_msg = 'Basic realm="{0}"'.format(self.auth_msg)

        headers = [('Content-Type', 'text/plain'),
                   ('Proxy-Authenticate', proxy_msg)]

        status_headers = StatusAndHeaders('407 Proxy Authentication', headers)

        value = self.auth_msg

        return WbResponse(status_headers, value=[value.encode('utf-8')])

    @staticmethod
    def read_basic_auth_coll(value):
        parts = value.split(' ')
        if parts[0].lower() != 'basic':
            return ''

        if len(parts) != 2:
            return ''

        user_pass = base64.b64decode(parts[1].encode('utf-8'))
        return to_native_str(user_pass.split(b':')[0])


#=================================================================
class IPCacheResolver(BaseCollResolver):
    def __init__(self, routes, config):
        super(IPCacheResolver, self).__init__(routes, config)
        self.cache = create_cache(config.get('redis_cache_key'))
        self.magic_name = config['magic_name']

    @property
    def supports_switching(self):
        return False

    def _get_ip(self, env):
        ip = env['REMOTE_ADDR']
        qs = env.get('pywb.proxy_query')
        if qs:
            res = parse_qs(qs)

            if 'ip' in res:
                ip = res['ip'][0]

        return ip

    def select_coll_response(self, env, default_coll=None):
        raise WbException('Invalid Proxy Collection Specified: ' + str(default_coll))

    def get_proxy_coll_ts(self, env):
        ip = env['REMOTE_ADDR']
        qs = env.get('pywb.proxy_query')

        if qs:
            res = parse_qs(qs)

            if 'ip' in res:
                ip = res['ip'][0]

            if 'delete' in res:
                del self.cache[ip + ':c']
                del self.cache[ip + ':t']
            else:
                if 'coll' in res:
                    self.cache[ip + ':c'] = res['coll'][0]

                if 'ts' in res:
                    self.cache[ip + ':t'] = res['ts'][0]

        coll = self.cache[ip + ':c']
        ts = self.cache[ip + ':t']
        return coll, ts

    def resolve(self, env):
        server_name = env['pywb.proxy_host']

        if self.magic_name in server_name:
            response = self.handle_magic_page(env)
            if response:
                return None, None, None, None, response

        return super(IPCacheResolver, self).resolve(env)

    def handle_magic_page(self, env):
        coll, ts = self.get_proxy_coll_ts(env)
        ip = self._get_ip(env)
        res = json.dumps({'ip': ip, 'coll': coll, 'ts': ts})
        return WbResponse.text_response(res, content_type='application/json')


#=================================================================
class CookieResolver(BaseCollResolver):
    SESH_COOKIE_NAME = '__pywb_proxy_sesh'

    def __init__(self, routes, config):
        super(CookieResolver, self).__init__(routes, config)
        self.magic_name = config['magic_name']
        self.sethost_prefix = '-sethost.' + self.magic_name + '.'
        self.set_prefix = '-set.' + self.magic_name

        self.cookie_name = config.get('cookie_name', self.SESH_COOKIE_NAME)
        self.proxy_select_view = config.get('proxy_select_view')

        self.extra_headers = config.get('extra_headers')

        self.cache = create_cache()

    @property
    def supports_switching(self):
        return True

    def get_proxy_coll_ts(self, env):
        coll, ts, sesh_id = self.get_coll(env)
        return coll, ts

    def select_coll_response(self, env, default_coll=None):
        return self.make_magic_response('auto',
                                        env['REL_REQUEST_URI'],
                                        env)

    def resolve(self, env):
        server_name = env['pywb.proxy_host']

        if ('.' + self.magic_name) in server_name:
            response = self.handle_magic_page(env)
            if response:
                return None, None, None, None, response

        return super(CookieResolver, self).resolve(env)

    def handle_magic_page(self, env):
        request_url = env['REL_REQUEST_URI']
        parts = urlsplit(request_url)
        server_name = env['pywb.proxy_host']

        path_url = parts.path[1:]
        if parts.query:
            path_url += '?' + parts.query

        if server_name.startswith('auto'):
            coll, ts, sesh_id = self.get_coll(env)

            if coll:
                return self.make_sethost_cookie_response(sesh_id,
                                                         path_url,
                                                         env)
            else:
                return self.make_magic_response('select', path_url, env)

        elif server_name.startswith('query.'):
            wb_url = WbUrl(path_url)

            # only dealing with specific timestamp setting
            if wb_url.is_query():
                return None

            coll, ts, sesh_id = self.get_coll(env)
            if not coll:
                return self.make_magic_response('select', path_url, env)

            self.set_ts(sesh_id, wb_url.timestamp)
            return self.make_redir_response(wb_url.url)

        elif server_name.endswith(self.set_prefix):
            old_sesh_id = extract_client_cookie(env, self.cookie_name)
            sesh_id = self.create_renew_sesh_id(old_sesh_id)

            if sesh_id != old_sesh_id:
                headers = self.make_cookie_headers(sesh_id, self.magic_name)
            else:
                headers = None

            coll = server_name[:-len(self.set_prefix)]

            # set sesh value
            self.set_coll(sesh_id, coll)

            return self.make_sethost_cookie_response(sesh_id, path_url, env,
                                                     headers=headers)

        elif self.sethost_prefix in server_name:
            inx = server_name.find(self.sethost_prefix)
            sesh_id = server_name[:inx]

            domain = server_name[inx + len(self.sethost_prefix):]

            headers = self.make_cookie_headers(sesh_id, domain)

            full_url = env['pywb.proxy_scheme'] + '://' + domain
            full_url += '/' + path_url
            return self.make_redir_response(full_url, headers=headers)

        elif 'select.' in server_name:
            coll, ts, sesh_id = self.get_coll(env)

            route_temp = '-set.' + self.magic_name + '/' + path_url

            return (self.proxy_select_view.
                    render_response(routes=self.routes,
                                    route_temp=route_temp,
                                    coll=coll,
                                    url=path_url))
        #else:
        #    msg = 'Invalid Magic Path: ' + url
        #    print msg
        #    return WbResponse.text_response(msg, status='404 Not Found')

    def make_cookie_headers(self, sesh_id, domain):
        cookie_val = '{0}={1}; Path=/; Domain=.{2}; HttpOnly'
        cookie_val = cookie_val.format(self.cookie_name, sesh_id, domain)
        headers = [('Set-Cookie', cookie_val)]
        return headers

    def make_sethost_cookie_response(self, sesh_id, path_url,
                                     env, headers=None):
        if '://' not in path_url:
            path_url = 'http://' + path_url

        path_parts = urlsplit(path_url)

        new_url = path_parts.path[1:]
        if path_parts.query:
            new_url += '?' + path_parts.query

        return self.make_magic_response(sesh_id + '-sethost', new_url, env,
                                        suffix=path_parts.netloc,
                                        headers=headers)

    def make_magic_response(self, prefix, url, env,
                            suffix=None, headers=None):
        full_url = env['pywb.proxy_scheme'] + '://' + prefix + '.'
        full_url += self.magic_name
        if suffix:
            full_url += '.' + suffix
        full_url += '/' + url
        return self.make_redir_response(full_url, headers=headers)

    def set_coll(self, sesh_id, coll):
        self.cache[sesh_id + ':c'] = coll

    def set_ts(self, sesh_id, ts):
        if ts:
            self.cache[sesh_id + ':t'] = ts
        # this ensures that omitting timestamp will reset to latest
        # capture by deleting the cache entry
        else:
            del self.cache[sesh_id + ':t']

    def get_coll(self, env):
        sesh_id = extract_client_cookie(env, self.cookie_name)

        coll = None
        ts = None
        if sesh_id:
            coll = self.cache[sesh_id + ':c']
            ts = self.cache[sesh_id + ':t']

        return coll, ts, sesh_id

    def create_renew_sesh_id(self, sesh_id, force=False):
        #if sesh_id in self.cache and not force:
        if sesh_id and ((sesh_id + ':c') in self.cache) and not force:
            return sesh_id

        sesh_id = base64.b32encode(os.urandom(5)).lower()
        return to_native_str(sesh_id)

    def make_redir_response(self, url, headers=None):
        if not headers:
            headers = []

        if self.extra_headers:
            for name, value in six.iteritems(self.extra_headers):
                headers.append((name, value))

        return WbResponse.redir_response(url, headers=headers)
