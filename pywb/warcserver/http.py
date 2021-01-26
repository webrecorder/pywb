import os

import requests
import six.moves.http_client
from requests.adapters import DEFAULT_POOLBLOCK, HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util.retry import Retry

six.moves.http_client._MAXHEADERS = 10000
six.moves.http_client._MAXLINE = 131072


# =============================================================================
class PywbHttpAdapter(HTTPAdapter):
    """This adaptor exists exists to restore the default behavior
    of urllib3 < 1.25.x, which was to not verify ssl certs,
    until a better solution is found
    """

    def __init__(self, cert_reqs='CERT_NONE', ca_cert_dir=None, **init_kwargs):
        self.cert_reqs = cert_reqs
        self.ca_cert_dir = ca_cert_dir
        return super(PywbHttpAdapter, self).__init__(**init_kwargs)

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
            cert_reqs=self.cert_reqs,
            ca_cert_dir=self.ca_cert_dir,
            **pool_kwargs
        )

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_kwargs['cert_reqs'] = self.cert_reqs
        proxy_kwargs['ca_cert_dir'] = self.ca_cert_dir
        return super(PywbHttpAdapter, self).proxy_manager_for(proxy, **proxy_kwargs)


# =============================================================================
class DefaultAdapters(object):
    live_adapter = PywbHttpAdapter(max_retries=Retry(3))
    remote_adapter = PywbHttpAdapter(max_retries=Retry(3))


requests.packages.urllib3.disable_warnings()

