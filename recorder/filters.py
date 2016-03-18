

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


