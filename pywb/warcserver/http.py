from requests.adapters import HTTPAdapter
import requests
import os

import six.moves.http_client
six.moves.http_client._MAXHEADERS = 10000

SOCKS_PORT = os.environ.get('SOCKS_PORT', 9050)
SOCKS_HOST = os.environ.get('SOCKS_HOST')
SOCKS_PROXIES = None

#=============================================================================
class DefaultAdapters(object):
    live_adapter = HTTPAdapter(max_retries=3)
    remote_adapter = HTTPAdapter(max_retries=3)

requests.packages.urllib3.disable_warnings()


#=============================================================================
def patch_socks():
    import socket
    import socks

    # Set socks proxy and wrap the urllib module
    socks.set_default_proxy(socks.PROXY_TYPE_SOCKS5, SOCKS_HOST, SOCKS_PORT, True)
    #socket.socket = socks.socksocket # sets default socket to be the sockipy socket

    # Perform DNS resolution through the socket
    orig_getaddrinfo = socks.socket.getaddrinfo

    def getaddrinfo(*args):
        if args[0] in ('127.0.0.1', 'localhost'):
            res = orig_getaddrinfo(*args)

        else:
            res = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]

        return res

    socks.socket.getaddrinfo = getaddrinfo

    socks_url = 'socks5h://{0}:{1}'.format(SOCKS_HOST, SOCKS_PORT)

    global SOCKS_PROXIES
    SOCKS_PROXIES = {'http': socks_url,
                     'https': socks_url}


#=============================================================================
if SOCKS_HOST:
    patch_socks()



