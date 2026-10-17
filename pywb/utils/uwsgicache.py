"""
Access to the caches of uWSGI, configured with its ``cache2`` option and
shared by all the uWSGI workers
"""


# =============================================================================
def get_uwsgi_cache(name):
    """Return the uWSGI cache ``name``, or None if pywb doesn't run in uWSGI
    or no cache with this name is configured.
    """
    try:
        import uwsgi
    except ImportError:
        return None

    if name not in get_uwsgi_cache_names(uwsgi):
        return None

    return UwsgiCache(uwsgi, name)


def get_uwsgi_cache_names(uwsgi):
    cache_opts = uwsgi.opt.get('cache2') or []
    if not isinstance(cache_opts, list):
        cache_opts = [cache_opts]

    names = set()
    for cache_opt in cache_opts:
        if isinstance(cache_opt, bytes):
            cache_opt = cache_opt.decode('utf-8')

        for setting in cache_opt.split(','):
            if setting.startswith('name='):
                names.add(setting[5:])

    return names


# =============================================================================
class UwsgiCache(object):
    def __init__(self, uwsgi, name):
        self.uwsgi = uwsgi
        self.name = name

    def get(self, key):
        """Return the value (bytes) for this key, or None"""
        return self.uwsgi.cache_get(key, self.name)

    def set(self, key, value, ttl):
        """Store the value (bytes) for this key, for ``ttl`` seconds"""
        # not stored if the cache is full or the value is too large
        self.uwsgi.cache_update(key, value, ttl, self.name)

    def __repr__(self):
        return "UwsgiCache('{0}')".format(self.name)
