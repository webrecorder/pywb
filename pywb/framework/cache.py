try:  # pragma: no cover
    import uwsgi
    uwsgi_cache = True
except ImportError:
    uwsgi_cache = False


from redis import StrictRedis
from pywb.utils.loaders import to_native_str


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
class DefaultCache(dict):
    def __getitem__(self, item):
        return self.get(item)


#=================================================================
class RedisCache(object):
    def __init__(self, redis_url):
        # must be of the form redis://host:port/db/key
        redis_url, key = redis_url.rsplit('/', 1)
        self.redis = StrictRedis.from_url(redis_url)
        self.key = key

    def __setitem__(self, item, value):
        self.redis.hset(self.key, item, value)

    def __getitem__(self, item):
        return to_native_str(self.redis.hget(self.key, item), 'utf-8')

    def __contains__(self, item):
        return self.redis.hexists(self.key, item)

    def __delitem__(self, item):
        self.redis.hdel(self.key, item)


#=================================================================
def create_cache(redis_url_key=None):
    if redis_url_key:
        return RedisCache(redis_url_key)

    if uwsgi_cache:  # pragma: no cover
        return UwsgiCache()
    else:
        return DefaultCache()
