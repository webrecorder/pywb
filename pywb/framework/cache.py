try:  # pragma: no cover
    import uwsgi
    uwsgi_cache = True
except ImportError:
    uwsgi_cache = False


#=================================================================
class UwsgiCache(object):  # pragma: no cover
    def __setitem__(self, item, value):
        uwsgi.cache_update(item, value)

    def __getitem__(self, item):
        return uwsgi.cache_get(item)

    def __contains__(self, item):
        return uwsgi.cache_exists(item)

    def __delitem__(self, item):
        uwsgi.cache_del(item)


#=================================================================
def create_cache():
    if uwsgi_cache:  # pragma: no cover
        return UwsgiCache()
    else:
        return {}
