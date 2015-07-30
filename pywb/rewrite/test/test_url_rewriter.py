"""
# urljoin tests

>>> UrlRewriter.urljoin('http://example.com/test/', '../file.html')
'http://example.com/file.html'

>>> UrlRewriter.urljoin('http://example.com/test/', '../path/../../../file.html')
'http://example.com/file.html'

>>> UrlRewriter.urljoin('http://example.com/test/', '/../file.html')
'http://example.com/file.html'

>>> UrlRewriter.urljoin('http://example.com/', '/abc/../../file.html')
'http://example.com/file.html'

>>> UrlRewriter.urljoin('http://example.com/path/more/', 'abc/../../file.html')
'http://example.com/path/file.html'

>>> UrlRewriter.urljoin('http://example.com/test/', 'file.html')
'http://example.com/test/file.html'

# UrlRewriter tests
>>> do_rewrite('other.html', '20131010/http://example.com/path/page.html', 'https://web.archive.org/web/')
'/web/20131010/http://example.com/path/other.html'

>>> do_rewrite('file.js', '20131010/http://example.com/path/page.html', 'https://web.archive.org/web/', 'js_')
'/web/20131010js_/http://example.com/path/file.js'

>>> do_rewrite('file.js', '20131010/http://example.com/', '/coll/')
'/coll/20131010/http://example.com/file.js'

>>> do_rewrite('file.js', '20131010/http://example.com', '/coll/', 'js_')
'/coll/20131010js_/http://example.com/file.js'

>>> do_rewrite('file.js', '20131010/http://example.com', '/coll/', '')
'/coll/20131010/http://example.com/file.js'

>>> do_rewrite('/other.html', '20130907*/http://example.com/path/page.html', 'http://localhost:8080/coll/')
'/coll/20130907*/http://example.com/other.html'

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

>>> do_rewrite('http://localhost:8080/web/2014im_/http://some-other-site.com', 'http://example.com/index.html', '/web/', full_prefix='http://localhost:8080/web/')
'http://localhost:8080/web/2014im_/http://some-other-site.com'

>>> do_rewrite('/web/http://some-other-site.com', 'http://example.com/index.html', '/web/', full_prefix='http://localhost:8080/web/')
'/web/http://some-other-site.com'

>>> do_rewrite(r'http:\/\/some-other-site.com', '20101226101112/http://example.com/index.html', 'https://localhost:8080/')
'https://localhost:8080/20101226101112/http:\\\\/\\\\/some-other-site.com'

>>> do_rewrite(r'//some-other-site.com', '20101226101112/http://example.com/index.html', 'http://localhost:8080/')
'//localhost:8080/20101226101112///some-other-site.com'

>>> do_rewrite(r'\/\/some-other-site.com', '20101226101112/http://example.com/index.html', 'http://localhost:8080/')
'//localhost:8080/20101226101112/\\\\/\\\\/some-other-site.com'

>>> do_rewrite(r'\\/\\/some-other-site.com', '20101226101112/http://example.com/index.html', 'https://localhost:8080/')
'//localhost:8080/20101226101112/\\\\/\\\\/some-other-site.com'

>>> do_rewrite(r'http:\/\/some-other-site.com', '20101226101112/http://example.com/index.html', 'https://localhost:8080/')
'https://localhost:8080/20101226101112/http:\\\\/\\\\/some-other-site.com'

>>> do_rewrite(r'http:\/\/some-other-site.com', '20101226101112/http://example.com/index.html', 'http://localhost:8080/')
'http://localhost:8080/20101226101112/http:\\\\/\\\\/some-other-site.com'

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

>>> do_rewrite('file:///some/path/', '20131010/http://example.com/path/page.html', 'https://web.archive.org/web/')
'file:///some/path/'

>>> UrlRewriter('19960708im_/http://domain.example.com/path.txt', '/abc/').get_new_url(url='')
'/abc/19960708im_/'

>>> UrlRewriter('2013id_/example.com/file/path/blah.html', '/123/').get_new_url(timestamp='20131024')
'/123/20131024id_/http://example.com/file/path/blah.html'

# deprefix tests
>>> do_deprefix('2013id_/http://example.com/file/path/blah.html?param=http://localhost:8080/pywb/20141226/http://example.com/', '/pywb/', 'http://localhost:8080/pywb/')
'http://example.com/file/path/blah.html?param=http://example.com/'

>>> do_deprefix('2013id_/http://example.com/file/path/blah.html?param=http://localhost:8080/pywb/if_/https://example.com/filename.html', '/pywb/', 'http://localhost:8080/pywb/')
'http://example.com/file/path/blah.html?param=https://example.com/filename.html'

>>> do_deprefix('2013id_/http://example.com/file/path/blah.html?param=http://localhost:8080/pywb/https://example.com/filename.html', '/pywb/', 'http://localhost:8080/pywb/')
'http://example.com/file/path/blah.html?param=https://example.com/filename.html'

>>> do_deprefix('http://example.com/file.html?param=http://localhost:8080/pywb/https%3A//example.com/filename.html&other=value&a=b&param2=http://localhost:8080/pywb/http://test.example.com', '/pywb/', 'http://localhost:8080/pywb/')
'http://example.com/file.html?param=https://example.com/filename.html&other=value&a=b&param2=http://test.example.com'

# urlencoded
>>> do_deprefix('http://example.com/file.html?foo=bar&url=' + urllib.quote_plus('http://localhost:8080/pywb/http://example.com/filename.html') + '&foo2=bar2', '/pywb/', 'http://localhost:8080/pywb/')
'http://example.com/file.html?foo=bar&url=http://example.com/filename.html&foo2=bar2'

# with extra path
>>> do_deprefix('http://example.com/file.html?foo=bar&url=' + urllib.quote_plus('http://localhost:8080/pywb/extra/path/http://example.com/filename.html') + '&foo2=bar2', '/pywb/', 'http://localhost:8080/pywb/')
'http://example.com/file.html?foo=bar&url=http://example.com/filename.html&foo2=bar2'

# HttpsUrlRewriter tests
>>> httpsrewriter = HttpsUrlRewriter('http://example.com/', None)
>>> httpsrewriter.rewrite('https://example.com/abc')
'http://example.com/abc'

>>> httpsrewriter.rewrite('http://example.com/abc')
'http://example.com/abc'

# rebase is identity
>>> httpsrewriter.rebase_rewriter('https://example.com/') == httpsrewriter
True

"""


from pywb.rewrite.url_rewriter import UrlRewriter, HttpsUrlRewriter
import urllib

def do_rewrite(rel_url, base_url, prefix, mod=None, full_prefix=None):
    rewriter = UrlRewriter(base_url, prefix, full_prefix=full_prefix)
    return rewriter.rewrite(rel_url, mod)


def do_deprefix(url, rel_prefix, full_prefix):
    rewriter = UrlRewriter(url, rel_prefix, full_prefix)
    url = rewriter.deprefix_url()
    return urllib.unquote_plus(url)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
