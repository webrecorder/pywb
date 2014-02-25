from wbrequestresponse import WbResponse, WbRequest
from archivalrouter import ArchivalRouter
import urlparse

#=================================================================
# An experimental router which combines both archival and proxy modes
# http proxy mode support is very simple: only latest capture is available currently
#=================================================================

class ProxyArchivalRouter:
    def __init__(self, routes, hostpaths = None, abs_path = True, home_view = None, error_view = None):
        self.archival = ArchivalRouter(routes, hostpaths, abs_path, home_view, error_view)
        self.proxy = ProxyRouter(routes[0].handler, hostpaths, error_view)
        self.error_view = error_view

    def __call__(self, env):
        response = self.archival(env)
        if response:
            return response

        response = self.proxy(env)
        if response:
            return response


#=================================================================
# Simple router which routes http proxy requests
# Handles requests of the form: GET  http://example.com
# Only supports latest capture replay at the moment
#=================================================================
class ProxyRouter:
    def __init__(self, handler, hostpaths = None, error_view = None):
        self.handler = handler
        self.hostpaths = hostpaths

        self.error_view = error_view

    def __call__(self, env):
        url = env['REL_REQUEST_URI']

        if url.endswith('/proxy.pac'):
            return self.make_pac_response(env)

        if not url.startswith('http://'):
            return None

        wbrequest = WbRequest(env,
                              request_uri=url,
                              wb_url_str=url,
                              #rel_prefix=url,
                              #host_prefix=self.hostpaths[0],
                              wburl_class=self.handler.get_wburl_type(),
                              urlrewriter_class=ProxyHttpsUrlRewriter,
                              use_abs_prefix=False,
                              is_proxy=True)

        return self.handler(wbrequest)


    # Proxy Auto-Config (PAC) script for the proxy
    def make_pac_response(self, env):
        server_hostport = env['SERVER_NAME'] + ':' + env['SERVER_PORT']

        buff = 'function FindProxyForURL (url, host) {\n'

        direct_cond ='    if (shExpMatch(host, "{0}")) {{ return "DIRECT"; }}\n'

        for hostpath in self.hostpaths:
            parts = urlparse.urlsplit(hostpath).netloc.split(':')
            buff += direct_cond.format(parts[0])

        buff += direct_cond.format(env['SERVER_NAME'])

        #buff += '\n    return "PROXY {0}";\n}}\n'.format(self.hostpaths[0])
        buff += '\n    return "PROXY {0}";\n}}\n'.format(server_hostport)

        return WbResponse.text_response(buff, content_type = 'application/x-ns-proxy-autoconfig')




#=================================================================
# A rewriter which only rewrites https -> http
#=================================================================
class ProxyHttpsUrlRewriter:
    HTTP = 'http://'
    HTTPS = 'https://'
    def __init__(self, wbrequest, prefix):
        pass

    def rewrite(self, url, mod = None):
        if url.startswith(self.HTTPS):
            return self.HTTP + url[len(self.HTTPS):]
        else:
            return url

    def get_timestamp_url(self, timestamp, url):
        return url

    def get_abs_url(self, url = ''):
        return url

