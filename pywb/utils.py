import itertools
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



#=================================================================
def unsurt(surt):
    """
    # Simple surt
    >>> unsurt('com,example)/')
    'example.com)/'

    # Broken surt
    >>> unsurt('com,example)')
    'com,example)'

    # Long surt
    >>> unsurt('suffix,domain,sub,subsub,another,subdomain)/path/file/index.html?a=b?c=)/')
    'subdomain.another.subsub.sub.domain.suffix)/path/file/index.html?a=b?c=)/'
    """

    try:
        index = surt.index(')/')
        parts = surt[0:index].split(',')
        parts.reverse()
        host = '.'.join(parts)
        host += surt[index:]
        return host

    except ValueError:
        # May not be a valid surt
        return surt


#=================================================================
# Support for bulk doctest testing via nose or py.test
# nosetests --with-doctest
# py.test --doctest_modules

import sys
is_in_testtool = any(sys.argv[0].endswith(tool) for tool in ['py.test', 'nosetests'])

def enable_doctests():
    return is_in_testtool


def test_data_dir():
    import os
    return os.path.dirname(os.path.realpath(__file__)) + '/../sample_archive/'

#=================================================================

if __name__ == "__main__" or enable_doctests():
    import doctest
    doctest.testmod()

