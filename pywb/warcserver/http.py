import os

import requests
import six.moves.http_client
from requests.adapters import DEFAULT_POOLBLOCK, HTTPAdapter
from urllib3.poolmanager import PoolManager

six.moves.http_client._MAXHEADERS = 10000
six.moves.http_client._MAXLINE = 131072

SOCKS_PROXIES = None
orig_getaddrinfo = None


class PywbHttpAdapter(HTTPAdapter):
    """This adaptor exists exists to restore the default behavior
    of urllib3 < 1.25.x, which was to not verify ssl certs,
    until a better solution is found
    """

    def init_poolmanager(
        self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs
    ):
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            strict=True,
            cert_reqs='CERT_NONE',
            **pool_kwargs
        )


# =============================================================================
class DefaultAdapters(object):
    live_adapter = PywbHttpAdapter(max_retries=3)
    remote_adapter = PywbHttpAdapter(max_retries=3)


requests.packages.urllib3.disable_warnings()


# =============================================================================
def patch_socks():
    try:
        import socks
    except ImportError:  # pragma: no cover
        print('Ignoring SOCKS_HOST: PySocks must be installed to use SOCKS proxy')
        return

    import socket

    socks_host = os.environ.get('SOCKS_HOST')
    socks_port = os.environ.get('SOCKS_PORT', 9050)

    # Set socks proxy and wrap the urllib module
    socks.set_default_proxy(socks.PROXY_TYPE_SOCKS5, socks_host, socks_port, True)
    # socket.socket = socks.socksocket # sets default socket to be the sockipy socket

    # store original getaddrinfo
    global orig_getaddrinfo
    orig_getaddrinfo = socks.socket.getaddrinfo

    # Perform DNS resolution through socket
    def getaddrinfo(*args):
        if args[0] in ('127.0.0.1', 'localhost'):
            res = orig_getaddrinfo(*args)

        else:
            res = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]

        return res

    socks.socket.getaddrinfo = getaddrinfo

    socks_url = 'socks5h://{0}:{1}'.format(socks_host, socks_port)

    global SOCKS_PROXIES
    SOCKS_PROXIES = {'http': socks_url, 'https': socks_url}


# =============================================================================
def unpatch_socks():
    global orig_getaddrinfo
    if not orig_getaddrinfo:
        return

    import socks

    socks.socket.getaddrinfo = orig_getaddrinfo
    orig_getaddrinfo = None

    global SOCKS_PROXIES
    SOCKS_PROXIES = None


# =============================================================================
if os.environ.get('SOCKS_HOST'):
    patch_socks()
