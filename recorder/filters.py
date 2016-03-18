from pywb.utils.timeutils import timestamp_to_datetime, datetime_to_iso_date


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
    def __call__(self, cdx):
        dt = timestamp_to_datetime(cdx['timestamp'])
        return ('revisit', cdx['url'], datetime_to_iso_date(dt))


# ============================================================================
class SkipDupePolicy(object):
    def __call__(self, cdx):
        return 'skip'


# ============================================================================
class WriteDupePolicy(object):
    def __call__(self, cdx):
        return 'write'

