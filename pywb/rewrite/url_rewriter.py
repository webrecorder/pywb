import copy
import urlparse

from wburl import WbUrl


#=================================================================
class UrlRewriter:
    """
    >>> do_rewrite('other.html', '20131010/http://example.com/path/page.html', 'https://web.archive.org/web/')
    'https://web.archive.org/web/20131010/http://example.com/path/other.html'

    >>> do_rewrite('file.js', '20131010/http://example.com/path/page.html', 'https://web.archive.org/web/', 'js_')
    'https://web.archive.org/web/20131010js_/http://example.com/path/file.js'

    >>> do_rewrite('/other.html', '20130907*/http://example.com/path/page.html', '/coll/')
    '/coll/20130907*/http://example.com/other.html'

    >>> do_rewrite('./other.html', '20130907*/http://example.com/path/page.html', '/coll/')
    '/coll/20130907*/http://example.com/path/other.html'

    >>> do_rewrite('../other.html', '20131112im_/http://example.com/path/page.html', '/coll/')
    '/coll/20131112im_/http://example.com/other.html'

    >>> do_rewrite('../../other.html', '*/http://example.com/index.html', 'localhost:8080/')
    'localhost:8080/*/http://example.com/other.html'

    >>> do_rewrite('path/../../other.html', '*/http://example.com/index.html', 'localhost:8080/')
    'localhost:8080/*/http://example.com/other.html'

    >>> do_rewrite('http://some-other-site.com', '20101226101112/http://example.com/index.html', 'localhost:8080/')
    'localhost:8080/20101226101112/http://some-other-site.com'

    >>> do_rewrite(r'http:\/\/some-other-site.com', '20101226101112/http://example.com/index.html', 'localhost:8080/')
    'localhost:8080/20101226101112/http:\\\\/\\\\/some-other-site.com'

    >>> do_rewrite('../../other.html', '2020/http://example.com/index.html', '/')
    '/2020/http://example.com/other.html'

    >>> do_rewrite('../../other.html', '2020/http://example.com/index.html', '')
    '2020/http://example.com/other.html'

    >>> do_rewrite('', '20131010010203/http://example.com/file.html', '/web/')
    '/web/20131010010203/http://example.com/file.html'

    >>> do_rewrite('#anchor', '20131010/http://example.com/path/page.html', 'https://web.archive.org/web/')
    '#anchor'

    >>> do_rewrite('mailto:example@example.com', '20131010/http://example.com/path/page.html', 'https://web.archive.org/web/')
    'mailto:example@example.com'

    >>> UrlRewriter('19960708im_/http://domain.example.com/path.txt', '/abc/').get_abs_url()
    '/abc/19960708im_/'

    >>> UrlRewriter('2013id_/example.com/file/path/blah.html', '/123/').get_timestamp_url('20131024')
    '/123/20131024id_/http://example.com/file/path/blah.html'
    """

    NO_REWRITE_URI_PREFIX = ['#', 'javascript:', 'data:', 'mailto:', 'about:']

    PROTOCOLS = ['http:', 'https:', '//', 'ftp:', 'mms:', 'rtsp:', 'wais:']

    def __init__(self, wburl, prefix):
        self.wburl = wburl if isinstance(wburl, WbUrl) else WbUrl(wburl)
        self.prefix = prefix

        #if self.prefix.endswith('/'):
        #    self.prefix = self.prefix[:-1]

    def rewrite(self, url, mod = None):
        # if special protocol, no rewriting at all
        if any (url.startswith(x) for x in self.NO_REWRITE_URI_PREFIX):
            return url

        wburl = self.wburl

        isAbs = any(url.startswith(x) for x in self.PROTOCOLS)

        # Optimized rewriter for
        # -rel urls that don't start with / and  don't contain ../ and no special mod
        if not (isAbs or mod or url.startswith('/') or ('../' in url)):
            finalUrl = urlparse.urljoin(self.prefix + wburl.original_url, url)

        else:
            # optimize: join if not absolute url, otherwise just use that
            if not isAbs:
                newUrl = urlparse.urljoin(wburl.url, url).replace('../', '')
            else:
                newUrl = url

            if mod is None:
                mod = wburl.mod

            finalUrl = self.prefix + wburl.to_str(mod=mod, url=newUrl)

        return finalUrl

    def get_abs_url(self, url = ''):
        return self.prefix + self.wburl.to_str(url=url)

    def get_timestamp_url(self, timestamp, url = None):
        if url is None:
            url = self.wburl.url

        return self.prefix + self.wburl.to_str(timestamp=timestamp, url=url)

    def set_base_url(self, newUrl):
        self.wburl.url = newUrl

    def __repr__(self):
        return "UrlRewriter('{0}', '{1}')".format(self.wburl, self.prefix)


def do_rewrite(rel_url, base_url, prefix, mod = None):
    rewriter = UrlRewriter(base_url, prefix)
    return rewriter.rewrite(rel_url, mod)


#=================================================================
class HttpsUrlRewriter:
    """
    A url rewriter which urls that start with https:// to http://
    Other urls/input is unchanged.

    >>> HttpsUrlRewriter(None, None).rewrite('https://example.com/abc')
    'http://example.com/abc'

    >>> HttpsUrlRewriter(None, None).rewrite('http://example.com/abc')
    'http://example.com/abc'
    """
    HTTP = 'http://'
    HTTPS = 'https://'

    def __init__(self, wburl, prefix):
        pass

    def rewrite(self, url, mod=None):
        if url.startswith(self.HTTPS):
            result = self.HTTP + url[len(self.HTTPS):]
            return result
        else:
            return url

    def get_timestamp_url(self, timestamp, url):
        return url

    def get_abs_url(self, url=''):
        return url

    def set_base_url(self, newUrl):
        pass
if __name__ == "__main__":
    import doctest
    doctest.testmod()



