from pywb.rewrite.rewrite_live import get_rewritten
from pywb.rewrite.url_rewriter import UrlRewriter

# This module has some rewriting tests against the 'live web'
# As such, the content may change and the test may break

urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html', '/pywb/')


def test_example_1():
    status_headers, buff = get_rewritten('http://example.com/', urlrewriter)

    # verify header rewriting
    assert (('X-Archive-Orig-connection', 'close') in status_headers.headers), status_headers


def test_example_2():
    status_headers, buff = get_rewritten('http://example.com/', urlrewriter)

    # verify header rewriting
    assert (('X-Archive-Orig-connection', 'close') in status_headers.headers), status_headers

    assert '/pywb/20131226101010/http://www.iana.org/domains/example' in buff, buff



def test_example_3():
    status_headers, buff = get_rewritten('http://archive.org/', urlrewriter)

    assert '/pywb/20131226101010/http://example.com/about/terms.php' in buff, buff


