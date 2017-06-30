from requests.adapters import HTTPAdapter

default_adapter = HTTPAdapter(max_retries=3)


