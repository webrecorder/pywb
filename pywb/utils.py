import itertools
import hmac
import time

def peek_iter(iterable):
    try:
        first = next(iterable)
    except StopIteration:
        return None

    return itertools.chain([first], iterable)


def get_header(headersList, name):
    nameLower = name.lower()
    for value in headersList:
        if (value[0].lower() == nameLower):
            return value[1]

class HMACCookieMaker:
    def __init__(self, key, name):
        self.key = key
        self.name = name


    def __call__(self, duration, extraId = ''):
        expire = str(long(time.time() + duration))

        if extraId:
            msg = extraId + '-' + expire
        else:
            msg = expire

        hmacdigest = hmac.new(self.key, msg)
        hexdigest = hmacdigest.hexdigest()

        if extraId:
            cookie = '{0}-{1}={2}-{3}'.format(self.name, extraId, expire, hexdigest)
        else:
            cookie = '{0}={1}-{2}'.format(self.name, expire, hexdigest)

        return cookie

        #return cookie + hexdigest



