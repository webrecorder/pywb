import redis
import pycdx_server.binsearch as binsearch
#======================================
# PrefixResolver - convert cdx file entry to url with prefix if url contains specified string
#======================================
def PrefixResolver(prefix, contains):
    def makeUrl(url):
        return [prefix + url] if (contains in url) else []

    return makeUrl

#======================================
class RedisResolver:
    def __init__(self, redisUrl, keyPrefix = 'w:'):
        self.redisUrl = redisUrl
        self.keyPrefix = keyPrefix
        self.redis = redis.StrictRedis.from_url(redisUrl)

    def __call__(self, filename):
        try:
            return [self.redis.hget(self.keyPrefix + filename, 'path')]
        except Exception as e:
            print e
            return None

#======================================
class PathIndexResolver:
    def __init__(self, pathindex_file):
        self.reader = binsearch.FileReader(pathindex_file)

    def __call__(self, filename):
        result = binsearch.iter_exact(self.reader, filename)

        def gen_list(result):
            for pathline in result:
                path = pathline.split('\t')
                if len(path) == 2:
                    yield path[1].rstrip()

        return gen_list(result)

