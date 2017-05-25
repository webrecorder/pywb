from warcio.timeutils import timestamp_to_datetime, datetime_to_iso_date
import re


# ============================================================================
# Header Exclusions
# ============================================================================
class ExcludeSpecificHeaders(object):
    def __init__(self, exclude_headers=None):
        self.exclude_headers = [x.lower() for x in exclude_headers]

    def __call__(self, header):
        if header[0].lower() in self.exclude_headers:
            return None

        return header


# ============================================================================
class ExcludeHttpOnlyCookieHeaders(object):
    HTTPONLY_RX = re.compile(';\\s*HttpOnly\\s*(;|$)', re.I)

    def __call__(self, header):
        name = header[0].lower()
        if name == 'cookie':
            return None

        if (name == 'set-cookie' and
            self.HTTPONLY_RX.search(header[1])):
            return None

        return header


# ============================================================================
# Revisit Policy
# ============================================================================
class WriteRevisitDupePolicy(object):
    def __call__(self, cdx, params):
        dt = timestamp_to_datetime(cdx['timestamp'])
        return ('revisit', cdx['url'], datetime_to_iso_date(dt))


# ============================================================================
class SkipDupePolicy(object):
    def __call__(self, cdx, params):
        if cdx['url'] == params['url']:
            return 'skip'
        else:
            return 'write'


# ============================================================================
class WriteDupePolicy(object):
    def __call__(self, cdx, params):
        return 'write'


# ============================================================================
# Skip Record Filters
# ============================================================================
class SkipNothingFilter(object):
    def skip_request(self, path, req_headers):
        return False

    def skip_response(self, path, req_headers, resp_headers):
        return False


# ============================================================================
class CollectionFilter(SkipNothingFilter):
    def __init__(self, accept_colls):
        self.rx_accept_map = {}

        if isinstance(accept_colls, str):
            self.rx_accept_map = {'*': re.compile(accept_colls)}

        elif isinstance(accept_colls, dict):
            for name in accept_colls:
                self.rx_accept_map[name] = re.compile(accept_colls[name])

    def skip_request(self, path, req_headers):
        if req_headers.get('Recorder-Skip') == '1':
            return True

        return False

    def skip_response(self, path, req_headers, resp_headers):
        if resp_headers.get('Recorder-Skip') == '1':
            return True

        path = path[1:].split('/', 1)[0]

        rx = self.rx_accept_map.get(path)
        if not rx:
            rx = self.rx_accept_map.get('*')

        if rx and not rx.match(resp_headers.get('WebAgg-Source-Coll', '')):
            return True

        return False


# ============================================================================
class SkipRangeRequestFilter(SkipNothingFilter):
    def skip_request(self, path, req_headers):
        range_ = req_headers.get('Range')
        if range_ and not range_.lower().startswith('bytes=0-'):
            return True

        return False


