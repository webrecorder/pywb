import re
import rfc3987

# aurl : ArchivalUrl representation for WB

class aurl:
    """
    # Replay Urls
    # ======================
    >>> print_test(aurl('/20131010000506/example.com'))
    ('replay', '20131010000506', None, 'example.com')

    >>> print_test(aurl('/20130102im_/example.com'))
    ('replay', '20130102', 'im_', 'example.com')

    >>> print_test(aurl('/https://example.com/xyz'))
    ('latest_replay', None, None, 'https://example.com/xyz')


    # Query Urls
    # ======================
    >>> print_test(aurl('/*/http://example.com/abc?def=a'))
    ('query', None, None, 'http://example.com/abc?def=a')


    # Error Urls
    # ======================
    >>> x = aurl('abc')
    Traceback (most recent call last):
    RequestParseException: Invalid WB Request Url: abc

    >>> x = aurl('/#$%#/')
    Traceback (most recent call last):
    RequestParseException: Bad Request Url: #$%#/

    >>> x = aurl('/http://example.com:abc/')
    Traceback (most recent call last):
    RequestParseException: Bad Request Url: http://example.com:abc/
    """

    # Regexs
    # ======================
    QUERY_REGEX = re.compile('^/(\d{1,14})?\*/(.*)$')
    REPLAY_REGEX = re.compile('^(/(\d{1,14})([a-z]{2}_)?)?/(.*)$')
    # ======================


    def __init__(self, url):
        self.original_url = url
        self.type = None
        self.url = None
        self.timestamp = None
        self.mod = None

        if not any (f(self, url) for f in [aurl._init_query, aurl._init_replay]):
            raise RequestParseException('Invalid WB Request Url: ' + url)

        matcher = rfc3987.match(self.url, 'URI_reference')

        if not matcher:
            raise RequestParseException('Bad Request Url: ' + self.url)

    # Match query regex
    # ======================
    def _init_query(self, url):
        query = aurl.QUERY_REGEX.match(url)
        if not query:
            return None

        self.timestamp = query.group(1)
        self.url = query.group(2)
        self.type = 'query'
        return True

    # Match replay regex
    # ======================
    def _init_replay(self, url):
        replay = aurl.REPLAY_REGEX.match(url)
        if not replay:
            return None

        self.timestamp = replay.group(2)
        self.mod = replay.group(3)
        self.url = replay.group(4)
        if self.timestamp:
            self.type = 'replay'
        else:
            self.type = 'latest_replay'

        return True


class RequestParseException(Exception):
    pass



if __name__ == "__main__":
    import doctest

    def print_test(self):
        return self.type, self.timestamp, self.mod, self.url

    doctest.testmod()
