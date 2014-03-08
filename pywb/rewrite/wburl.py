#!/usr/bin/python

"""
WbUrl represents the standard wayback archival url format.
A regular url is a subset of the WbUrl (latest replay).

The WbUrl expresses the common interface for interacting
with the wayback machine.

There WbUrl may represent one of the following forms:

query form: [/modifier]/[timestamp][-end_timestamp]*/<url>

modifier, timestamp and end_timestamp are optional

*/example.com
20101112030201*/http://example.com
2009-2015*/http://example.com
/cdx/*/http://example.com

url query form: used to indicate query across urls
same as query form but with a final *
*/example.com*
20101112030201*/http://example.com*


replay form:
20101112030201/http://example.com
20101112030201im_/http://example.com

latest_replay: (no timestamp)
http://example.com

Additionally, the BaseWbUrl provides the base components
(url, timestamp, end_timestamp, modifier, type) which
can be used to provide a custom representation of the
wayback url format.

"""

import re
import rfc3987


#=================================================================
class BaseWbUrl(object):
    QUERY = 'query'
    URL_QUERY = 'url_query'
    REPLAY = 'replay'
    LATEST_REPLAY = 'latest_replay'


    def __init__(self, url='', mod='',
                 timestamp='', end_timestamp='', type=None):

        self.url = url
        self.timestamp = timestamp
        self.end_timestamp = end_timestamp
        self.mod = mod
        self.type = type


#=================================================================
class WbUrl(BaseWbUrl):
    """
    # Replay Urls
    # ======================
    >>> repr(WbUrl('20131010000506/example.com'))
    "('replay', '20131010000506', '', 'http://example.com', '20131010000506/http://example.com')"

    >>> repr(WbUrl('20130102im_/https://example.com'))
    "('replay', '20130102', 'im_', 'https://example.com', '20130102im_/https://example.com')"

    >>> repr(WbUrl('20130102im_/https:/example.com'))
    "('replay', '20130102', 'im_', 'https://example.com', '20130102im_/https://example.com')"

    # Protocol agnostic convert to http
    >>> repr(WbUrl('20130102im_///example.com'))
    "('replay', '20130102', 'im_', 'http://example.com', '20130102im_/http://example.com')"

    >>> repr(WbUrl('cs_/example.com'))
    "('latest_replay', '', 'cs_', 'http://example.com', 'cs_/http://example.com')"

    >>> repr(WbUrl('https://example.com/xyz'))
    "('latest_replay', '', '', 'https://example.com/xyz', 'https://example.com/xyz')"

    >>> repr(WbUrl('https:/example.com/xyz'))
    "('latest_replay', '', '', 'https://example.com/xyz', 'https://example.com/xyz')"

    >>> repr(WbUrl('https://example.com/xyz?a=%2f&b=%2E'))
    "('latest_replay', '', '', 'https://example.com/xyz?a=%2f&b=%2E', 'https://example.com/xyz?a=%2f&b=%2E')"

    # Query Urls
    # ======================
    >>> repr(WbUrl('*/http://example.com/abc?def=a'))
    "('query', '', '', 'http://example.com/abc?def=a', '*/http://example.com/abc?def=a')"

    >>> repr(WbUrl('*/http://example.com/abc?def=a*'))
    "('url_query', '', '', 'http://example.com/abc?def=a', '*/http://example.com/abc?def=a*')"

    >>> repr(WbUrl('2010*/http://example.com/abc?def=a'))
    "('query', '2010', '', 'http://example.com/abc?def=a', '2010*/http://example.com/abc?def=a')"

    # timestamp range query
    >>> repr(WbUrl('2009-2015*/http://example.com/abc?def=a'))
    "('query', '2009', '', 'http://example.com/abc?def=a', '2009-2015*/http://example.com/abc?def=a')"

    >>> repr(WbUrl('json/*/http://example.com/abc?def=a'))
    "('query', '', 'json', 'http://example.com/abc?def=a', 'json/*/http://example.com/abc?def=a')"

    >>> repr(WbUrl('timemap-link/2011*/http://example.com/abc?def=a'))
    "('query', '2011', 'timemap-link', 'http://example.com/abc?def=a', 'timemap-link/2011*/http://example.com/abc?def=a')"

    # strip off repeated, likely scheme-agnostic, slashes altogether
    >>> repr(WbUrl('///example.com'))
    "('latest_replay', '', '', 'http://example.com', 'http://example.com')"

    >>> repr(WbUrl('//example.com/'))
    "('latest_replay', '', '', 'http://example.com/', 'http://example.com/')"

    >>> repr(WbUrl('/example.com/'))
    "('latest_replay', '', '', 'http://example.com/', 'http://example.com/')"


    # Error Urls
    # ======================
    >>> x = WbUrl('/#$%#/')
    Traceback (most recent call last):
    Exception: Bad Request Url: http://#$%#/

    >>> x = WbUrl('/http://example.com:abc/')
    Traceback (most recent call last):
    Exception: Bad Request Url: http://example.com:abc/

    # considered blank
    >>> x = WbUrl('https:/')
    >>> x = WbUrl('https:///')
    >>> x = WbUrl('http://')
    """

    # Regexs
    # ======================
    QUERY_REGEX = re.compile('^(?:([\w\-:]+)/)?(\d*)(?:-(\d+))?\*/?(.*)$')
    REPLAY_REGEX = re.compile('^(\d*)([a-z]+_)?/{0,3}(.*)$')

    DEFAULT_SCHEME = 'http://'
    # ======================


    def __init__(self, url):
        super(WbUrl, self).__init__()

        self.original_url = url

        if not any (f(url) for f in [self._init_query, self._init_replay]):
            raise Exception('Invalid WbUrl: ', url)

        if len(self.url) == 0:
            raise Exception('Invalid WbUrl: ', url)

        # protocol agnostic url -> http://
        # no protocol -> http://
        inx = self.url.find(':/')
        if inx < 0:
            self.url = self.DEFAULT_SCHEME + self.url
        else:
            inx += 2
            if inx < len(self.url) and self.url[inx] != '/':
                self.url = self.url[:inx] + '/' + self.url[inx:]

        # BUG?: adding upper() because rfc3987 lib rejects lower case %-encoding
        # %2F is fine, but %2f -- standard supports either
        matcher = rfc3987.match(self.url.upper(), 'IRI')

        if not matcher:
            raise Exception('Bad Request Url: ' + self.url)

    # Match query regex
    # ======================
    def _init_query(self, url):
        query = self.QUERY_REGEX.match(url)
        if not query:
            return None

        res = query.groups('')

        self.mod = res[0]
        self.timestamp = res[1]
        self.end_timestamp = res[2]
        self.url = res[3]
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
        end_timestamp = overrides['end_timestamp'] if 'end_timestamp' in overrides else self.end_timestamp
        url = overrides['url'] if 'url' in overrides else self.url

        if atype == self.QUERY or atype == self.URL_QUERY:
            tsmod = ''
            if mod:
                tsmod += mod + "/"
            if timestamp:
                tsmod += timestamp
            if end_timestamp:
                tsmod += '-' + end_timestamp

            tsmod += "*/" + url
            if atype == self.URL_QUERY:
                tsmod += "*"
            return tsmod
        else:
            tsmod = timestamp + mod
            if len(tsmod) > 0:
                return tsmod + "/" + url
            else:
                return url

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return str((self.type, self.timestamp, self.mod, self.url, str(self)))

if __name__ == "__main__":
    import doctest
    doctest.testmod()
