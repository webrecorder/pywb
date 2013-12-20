#!/usr/bin/python

import re
import rfc3987

import wbexceptions

# ArchivalUrl : archivalurl representation for WB

class ArchivalUrl:
    """
    # Replay Urls
    # ======================
    >>> repr(ArchivalUrl('/20131010000506/example.com'))
    "('replay', '20131010000506', '', 'http://example.com', '/20131010000506/http://example.com')"

    >>> repr(ArchivalUrl('/20130102im_/https://example.com'))
    "('replay', '20130102', 'im_', 'https://example.com', '/20130102im_/https://example.com')"

    >>> repr(ArchivalUrl('/cs_/example.com'))
    "('latest_replay', '', 'cs_', 'http://example.com', '/cs_/http://example.com')"

    >>> repr(ArchivalUrl('/https://example.com/xyz'))
    "('latest_replay', '', '', 'https://example.com/xyz', '/https://example.com/xyz')"


    # Query Urls
    # ======================
    >>> repr(ArchivalUrl('/*/http://example.com/abc?def=a'))
    "('query', '', '', 'http://example.com/abc?def=a', '/*/http://example.com/abc?def=a')"

    >>> repr(ArchivalUrl('/*/http://example.com/abc?def=a*'))
    "('url_query', '', '', 'http://example.com/abc?def=a', '/*/http://example.com/abc?def=a*')"

    >>> repr(ArchivalUrl('/json/*/http://example.com/abc?def=a'))
    "('query', '', 'json', 'http://example.com/abc?def=a', '/json/*/http://example.com/abc?def=a')"

    >>> repr(ArchivalUrl('/timemap-link/2011*/http://example.com/abc?def=a'))
    "('query', '2011', 'timemap-link', 'http://example.com/abc?def=a', '/timemap-link/2011*/http://example.com/abc?def=a')"


    # Error Urls
    # ======================
    >>> x = ArchivalUrl('abc')
    Traceback (most recent call last):
    RequestParseException: Invalid WB Request Url: abc

    >>> x = ArchivalUrl('/#$%#/')
    Traceback (most recent call last):
    BadUrlException: Bad Request Url: http://#$%#/

    >>> x = ArchivalUrl('/http://example.com:abc/')
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

        if not any (f(self, url) for f in [ArchivalUrl._init_query, ArchivalUrl._init_replay]):
            raise wbexceptions.RequestParseException('Invalid WB Request Url: ' + url)

        if len(self.url) == 0:
            raise wbexceptions.RequestParseException('Invalid WB Request Url: ' + url)

        if not self.url.startswith('//') and not '://' in self.url:
            self.url = ArchivalUrl.DEFAULT_SCHEME + self.url

        matcher = rfc3987.match(self.url, 'IRI')

        if not matcher:
            raise wbexceptions.BadUrlException('Bad Request Url: ' + self.url)

    # Match query regex
    # ======================
    def _init_query(self, url):
        query = ArchivalUrl.QUERY_REGEX.match(url)
        if not query:
            return None

        res = query.groups('')

        self.mod = res[0]
        self.timestamp = res[1]
        self.url = res[2]
        if self.url.endswith('*'):
            self.type = ArchivalUrl.URL_QUERY
            self.url = self.url[:-1]
        else:
            self.type = ArchivalUrl.QUERY
        return True

    # Match replay regex
    # ======================
    def _init_replay(self, url):
        replay = ArchivalUrl.REPLAY_REGEX.match(url)
        if not replay:
            return None

        res = replay.groups('')

        self.timestamp = res[0]
        self.mod = res[1]
        self.url = res[2]
        if self.timestamp:
            self.type = ArchivalUrl.REPLAY
        else:
            self.type = ArchivalUrl.LATEST_REPLAY

        return True

    # Str Representation
    # ====================
    def __str__(self):
        if self.type == ArchivalUrl.QUERY or self.type == ArchivalUrl.URL_QUERY:
            tsmod = "/"
            if self.mod:
                tsmod += self.mod + "/"
            if self.timestamp:
                tsmod += self.timestamp

            tsmod += "*/" + self.url
            if self.type == ArchivalUrl.URL_QUERY:
                tsmod += "*"
            return tsmod
        else:
            tsmod = self.timestamp + self.mod
            if len(tsmod) > 0:
                return "/" + tsmod + "/" + self.url
            else:
                return "/" + self.url

    def __repr__(self):
        return str((self.type, self.timestamp, self.mod, self.url, str(self)))

if __name__ == "__main__":
    import doctest
    doctest.testmod()
