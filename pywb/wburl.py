#!/usr/bin/python

import re
import rfc3987

import wbexceptions

# WbUrl : wb archival url representation for WB

class WbUrl:
    """
    # Replay Urls
    # ======================
    >>> repr(WbUrl('/20131010000506/example.com'))
    "('replay', '20131010000506', '', 'http://example.com', '/20131010000506/http://example.com')"

    >>> repr(WbUrl('/20130102im_/https://example.com'))
    "('replay', '20130102', 'im_', 'https://example.com', '/20130102im_/https://example.com')"

    # Protocol agnostic convert to http
    >>> repr(WbUrl('/20130102im_///example.com'))
    "('replay', '20130102', 'im_', 'http://example.com', '/20130102im_/http://example.com')"

    >>> repr(WbUrl('/cs_/example.com'))
    "('latest_replay', '', 'cs_', 'http://example.com', '/cs_/http://example.com')"

    >>> repr(WbUrl('/https://example.com/xyz'))
    "('latest_replay', '', '', 'https://example.com/xyz', '/https://example.com/xyz')"

    >>> repr(WbUrl('/https://example.com/xyz?a=%2f&b=%2E'))
    "('latest_replay', '', '', 'https://example.com/xyz?a=%2f&b=%2E', '/https://example.com/xyz?a=%2f&b=%2E')"

    # Query Urls
    # ======================
    >>> repr(WbUrl('/*/http://example.com/abc?def=a'))
    "('query', '', '', 'http://example.com/abc?def=a', '/*/http://example.com/abc?def=a')"

    >>> repr(WbUrl('/*/http://example.com/abc?def=a*'))
    "('url_query', '', '', 'http://example.com/abc?def=a', '/*/http://example.com/abc?def=a*')"

    >>> repr(WbUrl('/json/*/http://example.com/abc?def=a'))
    "('query', '', 'json', 'http://example.com/abc?def=a', '/json/*/http://example.com/abc?def=a')"

    >>> repr(WbUrl('/timemap-link/2011*/http://example.com/abc?def=a'))
    "('query', '2011', 'timemap-link', 'http://example.com/abc?def=a', '/timemap-link/2011*/http://example.com/abc?def=a')"


    # Error Urls
    # ======================
    >>> x = WbUrl('abc')
    Traceback (most recent call last):
    RequestParseException: Invalid WB Request Url: abc

    >>> x = WbUrl('/#$%#/')
    Traceback (most recent call last):
    BadUrlException: Bad Request Url: http://#$%#/

    >>> x = WbUrl('/http://example.com:abc/')
    Traceback (most recent call last):
    BadUrlException: Bad Request Url: http://example.com:abc/
    """

    # Regexs
    # ======================
    QUERY_REGEX = re.compile('^/?([\w\-:]+)?/(\d*)\*/(.*)$')
    REPLAY_REGEX = re.compile('^/(\d*)([a-z]+_)?/?(.*)$')

    QUERY = 'query'
    URL_QUERY = 'url_query'
    REPLAY = 'replay'
    LATEST_REPLAY = 'latest_replay'

    DEFAULT_SCHEME = 'http://'
    # ======================


    def __init__(self, url):
        self.original_url = url
        self.type = None
        self.url = ''
        self.timestamp = ''
        self.mod = ''

        if not any (f(url) for f in [self._init_query, self._init_replay]):
            raise wbexceptions.RequestParseException('Invalid WB Request Url: ' + url)

        if len(self.url) == 0:
            raise wbexceptions.RequestParseException('Invalid WB Request Url: ' + url)

        # protocol agnostic url -> http://
        if self.url.startswith('//'):
            self.url = self.DEFAULT_SCHEME + self.url[2:]
        # no protocol -> http://
        elif not '://' in self.url:
            self.url = self.DEFAULT_SCHEME + self.url

        # BUG?: adding upper() because rfc3987 lib rejects lower case %-encoding
        # %2F is fine, but %2f -- standard supports either
        matcher = rfc3987.match(self.url.upper(), 'IRI')

        if not matcher:
            raise wbexceptions.BadUrlException('Bad Request Url: ' + self.url)

    # Match query regex
    # ======================
    def _init_query(self, url):
        query = self.QUERY_REGEX.match(url)
        if not query:
            return None

        res = query.groups('')

        self.mod = res[0]
        self.timestamp = res[1]
        self.url = res[2]
        if self.url.endswith('*'):
            self.type = self.URL_QUERY
            self.url = self.url[:-1]
        else:
            self.type = self.QUERY
        return True

    # Match replay regex
    # ======================
    def _init_replay(self, url):
        replay = self.REPLAY_REGEX.match(url)
        if not replay:
            return None

        res = replay.groups('')

        self.timestamp = res[0]
        self.mod = res[1]
        self.url = res[2]
        if self.timestamp:
            self.type = self.REPLAY
        else:
            self.type = self.LATEST_REPLAY

        return True

    # Str Representation
    # ====================
    def to_str(self, **overrides):
        atype = overrides['type'] if 'type' in overrides else self.type
        mod = overrides['mod'] if 'mod' in overrides else self.mod
        timestamp = overrides['timestamp'] if 'timestamp' in overrides else self.timestamp
        url = overrides['url'] if 'url' in overrides else self.url

        if atype == self.QUERY or atype == self.URL_QUERY:
            tsmod = "/"
            if mod:
                tsmod += mod + "/"
            if timestamp:
                tsmod += timestamp

            tsmod += "*/" + url
            if atype == self.URL_QUERY:
                tsmod += "*"
            return tsmod
        else:
            tsmod = timestamp + mod
            if len(tsmod) > 0:
                return "/" + tsmod + "/" + url
            else:
                return "/" + url

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return str((self.type, self.timestamp, self.mod, self.url, str(self)))

if __name__ == "__main__":
    import doctest
    doctest.testmod()
