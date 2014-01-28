import redis
import binsearch
#======================================
# PrefixResolver - convert cdx file entry to url with prefix if url contains specified string
#======================================
def PrefixResolver(prefix, contains = ''):
    def makeUrl(url):
        return [prefix + url] if (contains in url) else []

    print "prefix: " + prefix + " contains: " + contains
    return makeUrl

#======================================
class RedisResolver:
    def __init__(self, redis_url, key_prefix = 'w:'):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.redis = redis.StrictRedis.from_url(redis_url)

    def __call__(self, filename):
        try:
            redis_val = self.redis.hget(self.key_prefix + filename, 'path')
            return [redis_val] if redis_val else None
        except Exception as e:
            print e
            return None

#======================================
class PathIndexResolver:
    def __init__(self, pathindex_file):
        self.reader = binsearch.FileReader(pathindex_file)

    def __call__(self, filename):
        result = binsearch.iter_exact(self.reader, filename, '\t')

        def gen_list(result):
            for pathline in result:
                path = pathline.split('\t')
                if len(path) == 2:
                    yield path[1]

        return gen_list(result)

