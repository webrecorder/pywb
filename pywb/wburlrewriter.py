import copy
import urlparse

from wbarchivalurl import ArchivalUrl

class ArchivalUrlRewriter:
    """
    >>> test_rewrite('other.html', '/20131010/http://example.com/path/page.html', 'https://web.archive.org/web/')
    'https://web.archive.org/web/20131010/http://example.com/path/other.html'

    >>> test_rewrite('file.js', '/20131010/http://example.com/path/page.html', 'https://web.archive.org/web/', 'js_')
    'https://web.archive.org/web/20131010js_/http://example.com/path/file.js'

    >>> test_rewrite('./other.html', '/20130907*/http://example.com/path/page.html', '/coll/')
    '/coll/20130907*/http://example.com/path/other.html'

    >>> test_rewrite('../other.html', '/20131112im_/http://example.com/path/page.html', '/coll/')
    '/coll/20131112im_/http://example.com/other.html'

    >>> test_rewrite('../../other.html', '/*/http://example.com/index.html', 'localhost:8080/')
    'localhost:8080/*/http://example.com/other.html'

    >>> test_rewrite('../../other.html', '/2020/http://example.com/index.html', '/')
    '/2020/http://example.com/other.html'

    >>> test_rewrite('../../other.html', '/2020/http://example.com/index.html', '')
    '/2020/http://example.com/other.html'
      """

    def __init__(self, wburl_str, prefix):
        self.wburl_str = wburl_str
        self.prefix = prefix
        if self.prefix.endswith('/'):
            self.prefix = self.prefix[:-1]

    def rewrite(self, rel_url, mod = None):
        if '../' in rel_url or mod:
            wburl = ArchivalUrl(self.wburl_str)
            wburl.url = urlparse.urljoin(wburl.url, rel_url)
            wburl.url = wburl.url.replace('../', '')
            if mod is not None:
                wburl.mod = mod

            final_url = self.prefix + str(wburl)
        else:
            final_url = urlparse.urljoin(self.prefix + self.wburl_str, rel_url)

        return final_url

if __name__ == "__main__":
    import doctest

    def test_rewrite(rel_url, base_url, prefix, mod = None):
        rewriter = ArchivalUrlRewriter(base_url, prefix)
        return rewriter.rewrite(rel_url, mod)

    doctest.testmod()
