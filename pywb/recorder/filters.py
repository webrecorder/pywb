from warcio.timeutils import timestamp_to_datetime, datetime_to_iso_date
import re


# ============================================================================
# Header Exclusions
# ============================================================================
class ExcludeNone(object):
    def __call__(self, record):
        return None


# ============================================================================
class ExcludeSpecificHeaders(object):
    def __init__(self, exclude_headers=[]):
        self.exclude_headers = [x.lower() for x in exclude_headers]

    def __call__(self, record):
        return self.exclude_headers


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
    def skip_request(self, req_headers):
        return False

    def skip_response(self, req_headers, resp_headers):
        return False


# ============================================================================
class CollectionFilter(SkipNothingFilter):
    def __init__(self, accept_colls):
        self.rx_accept_colls = re.compile(accept_colls)

    def skip_request(self, req_headers):
        if req_headers.get('Recorder-Skip') == '1':
            return True

        return False

    def skip_response(self, req_headers, resp_headers):
        if not self.rx_accept_colls.match(resp_headers.get('WebAgg-Source-Coll', '')):
            return True

        return False


# ============================================================================
class SkipRangeRequestFilter(SkipNothingFilter):
    def skip_request(self, req_headers):
        range_ = req_headers.get('Range')
        if range_ and not range_.lower().startswith('bytes=0-'):
            return True

        return False


