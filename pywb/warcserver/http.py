from requests.adapters import HTTPAdapter

class DefaultAdapters(object):
    live_adapter = HTTPAdapter(max_retries=3)
    remote_adapter = HTTPAdapter(max_retries=3)


