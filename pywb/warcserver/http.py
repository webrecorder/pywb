from requests.adapters import HTTPAdapter

class DefaultAdapters(object):
    live_adapter = HTTPAdapter(max_retries=3)
    remote_adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8, pool_block=True)


