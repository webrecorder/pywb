#!/usr/bin/python

import re
import rfc3987

import wbexceptions

# aurl : ArchivalUrl representation for WB

class aurl:
    """
    # Replay Urls
    # ======================
    >>> repr(aurl('/20131010000506/example.com'))
    "('replay', '20131010000506', '', 'example.com', '/20131010000506/example.com')"

    >>> repr(aurl('/20130102im_/example.com'))
    "('replay', '20130102', 'im_', 'example.com', '/20130102im_/example.com')"

    >>> repr(aurl('/cs_/example.com'))
    "('latest_replay', '', 'cs_', 'example.com', '/cs_/example.com')"

    >>> repr(aurl('/https://example.com/xyz'))
    "('latest_replay', '', '', 'https://example.com/xyz', '/https://example.com/xyz')"


    # Query Urls
    # ======================
    >>> repr(aurl('/*/http://example.com/abc?def=a'))
    "('query', '', '', 'http://example.com/abc?def=a', '/*/http://example.com/abc?def=a')"


    # Error Urls
    # ======================
    >>> x = aurl('abc')
    Traceback (most recent call last):
    RequestParseException: Invalid WB Request Url: abc

    >>> x = aurl('/#$%#/')
    Traceback (most recent call last):
    BadUrlException: Bad Request Url: #$%#/

    >>> x = aurl('/http://example.com:abc/')
    Traceback (most recent call last):
    BadUrlException: Bad Request Url: http://example.com:abc/
    """

    # Regexs
    # ======================
    QUERY_REGEX = re.compile('^/(\d{1,14})?\*/(.*)$')
    REPLAY_REGEX = re.compile('^/(\d{1,14})?([a-z]{2}_)?/?(.*)$')
    # ======================


    def __init__(self, url):
        self.original_url = url
        self.type = None
        self.url = ''
        self.timestamp = ''
        self.mod = ''

        if not any (f(self, url) for f in [aurl._init_query, aurl._init_replay]):
            raise wbexceptions.RequestParseException('Invalid WB Request Url: ' + url)

        matcher = rfc3987.match(self.url, 'IRI_reference')

        if not matcher:
            raise wbexceptions.BadUrlException('Bad Request Url: ' + self.url)

    # Match query regex
    # ======================
    def _init_query(self, url):
        query = aurl.QUERY_REGEX.match(url)
        if not query:
            return None

        res = query.groups('')

        self.timestamp = res[0]
        self.url = res[1]
        self.type = 'query'
        return True

    # Match replay regex
    # ======================
    def _init_replay(self, url):
        replay = aurl.REPLAY_REGEX.match(url)
        if not replay:
            return None

        res = replay.groups('')

        self.timestamp = res[0]
        self.mod = res[1]
        self.url = res[2]
        if self.timestamp:
            self.type = 'replay'
        else:
            self.type = 'latest_replay'

        return True

    # Str Representation
    # ====================
    def __str__(self):
        if self.type == 'query':
            return "/*/" + self.url
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

    #def print_test(self):
    #    return self.type, self.timestamp, self.mod, self.url, str(self)

    doctest.testmod()
