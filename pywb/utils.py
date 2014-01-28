import itertools
import hmac
import time
import zlib
import time
import datetime
import calendar
import re

def peek_iter(iterable):
    try:
        first = next(iterable)
    except StopIteration:
        return None

    return itertools.chain([first], iterable)


def split_prefix(key, prefixs):
    for p in prefixs:
        if key.startswith(p):
            plen = len(p)
            return (key[:plen], key[plen:])


def create_decompressor():
    return zlib.decompressobj(16 + zlib.MAX_WBITS)

#=================================================================
# Cookie Signing
#=================================================================

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


#=================================================================
# Adapted from example at
class PerfTimer:
    def __init__(self, perfdict, name):
        self.perfdict = perfdict
        self.name = name

    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        if self.perfdict is not None:
            self.perfdict[self.name] = str(self.end - self.start)


#=================================================================
# str <-> datetime conversion
#=================================================================

DATE_TIMESPLIT = re.compile('[^\d]')

TIMESTAMP_14 = '%Y%m%d%H%M%S'

PAD_STAMP_END = '29991231235959'



def iso_date_to_datetime(string):
    """
    >>> iso_date_to_datetime('2013-12-26T10:11:12Z')
    datetime.datetime(2013, 12, 26, 10, 11, 12)

    >>> iso_date_to_datetime('2013-12-26T10:11:12Z')
    datetime.datetime(2013, 12, 26, 10, 11, 12)
     """

    nums = DATE_TIMESPLIT.split(string)
    if nums[-1] == '':
        nums = nums[:-1]

    dt = datetime.datetime(*map(int, nums))
    return dt

def datetime_to_timestamp(dt):
    """
    >>> datetime_to_timestamp(datetime.datetime(2013, 12, 26, 10, 11, 12))
    '20131226101112'
    """

    return dt.strftime(TIMESTAMP_14)

def iso_date_to_timestamp(string):
    """
    >>> iso_date_to_timestamp('2013-12-26T10:11:12Z')
    '20131226101112'

    >>> iso_date_to_timestamp('2013-12-26T10:11:12')
    '20131226101112'
     """

    return datetime_to_timestamp(iso_date_to_datetime(string))


# default pad is end of range for compatibility
def pad_timestamp(string, pad_str = PAD_STAMP_END):
    """
    >>> pad_timestamp('20')
    '20991231235959'

    >>> pad_timestamp('2014')
    '20141231235959'

    >>> pad_timestamp('20141011')
    '20141011235959'

    >>> pad_timestamp('201410110010')
    '20141011001059'
     """

    str_len = len(string)
    pad_len = len(pad_str)

    return string if str_len >= pad_len else string + pad_str[str_len:]


def timestamp_to_datetime(string):
    """
    >>> timestamp_to_datetime('20131226095010')
    time.struct_time(tm_year=2013, tm_mon=12, tm_mday=26, tm_hour=9, tm_min=50, tm_sec=10, tm_wday=3, tm_yday=360, tm_isdst=-1)

    >>> timestamp_to_datetime('2014')
    time.struct_time(tm_year=2014, tm_mon=12, tm_mday=31, tm_hour=23, tm_min=59, tm_sec=59, tm_wday=2, tm_yday=365, tm_isdst=-1)
    """

    # Default pad to end of range for comptability
    return time.strptime(pad_timestamp(string), TIMESTAMP_14)


def timestamp_to_sec(string):
    """
    >>> timestamp_to_sec('20131226095010')
    1388051410

    >>> timestamp_to_sec('2014')
    1420070399
    """

    return calendar.timegm(timestamp_to_datetime(string))

# adapted -from wsgiref.request_uri, but doesn't include domain name and allows all characters
# allowed in the path segment according to: http://tools.ietf.org/html/rfc3986#section-3.3
# explained here: http://stackoverflow.com/questions/4669692/valid-characters-for-directory-part-of-a-url-for-short-links
def rel_request_uri(environ, include_query=1):
    """
    Return the requested path, optionally including the query string

    # Simple test:
    >>> rel_request_uri({'PATH_INFO': '/web/example.com'})
    '/web/example.com'

    # Test all unecoded special chars and double-quote
    # (double-quote must be encoded but not single quote)
    >>> rel_request_uri({'PATH_INFO': "/web/example.com/0~!+$&'()*+,;=:\\\""})
    "/web/example.com/0~!+$&'()*+,;=:%22"
    """
    from urllib import quote
    url = quote(environ.get('PATH_INFO',''), safe='/~!$&\'()*+,;=:@')
    if include_query and environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']

    return url



#============================================
# Support for bulk doctest testing via nose
# nosetests --with-doctest

import sys
is_in_nose = sys.argv[0].endswith('nosetests')

def enable_doctests():
    return is_in_nose

#============================================

if __name__ == "__main__" or enable_doctests():
    import doctest
    doctest.testmod()

