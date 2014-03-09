from wbrequestresponse import WbResponse, WbRequest
from archivalrouter import ArchivalRouter
import urlparse

from pywb.rewrite.url_rewriter import HttpsUrlRewriter

#=================================================================
# An experimental router which combines both archival and proxy modes
# http proxy mode support is very simple so far:
# only latest capture is available currently
#=================================================================
class ProxyArchivalRouter(ArchivalRouter):
    def __init__(self, routes,
                 hostpaths=None,
                 port=None,
                 abs_path=True,
                 home_view=None,
                 error_view=None):

        (super(ProxyArchivalRouter, self).
                              __init__(routes,
                                       hostpaths=hostpaths,
                                       port=port,
                                       abs_path=abs_path,
                                       home_view=home_view,
                                       error_view=error_view))

        self.proxy = ProxyRouter(routes[0].handler, hostpaths, error_view)
        #self.error_view = error_view

    def __call__(self, env):
        response = self.proxy(env)
        if response:
            return response

        response = super(ProxyArchivalRouter, self).__call__(env)
        if response:
            return response


#=================================================================
# Simple router which routes http proxy requests
# Handles requests of the form: GET  http://example.com
# Only supports latest capture replay at the moment
#=================================================================
class ProxyRouter:
    def __init__(self, handler, hostpaths=None, error_view=None):
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
                              host_prefix=self.hostpaths[0],
                              wburl_class=self.handler.get_wburl_type(),
                              urlrewriter_class=HttpsUrlRewriter,
                              use_abs_prefix=False,
                              is_proxy=True)

        return self.handler(wbrequest)

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
