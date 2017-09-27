from requests.adapters import HTTPAdapter
import requests

class DefaultAdapters(object):
    live_adapter = HTTPAdapter(max_retries=3)
    remote_adapter = HTTPAdapter(max_retries=3)

requests.packages.urllib3.disable_warnings()

