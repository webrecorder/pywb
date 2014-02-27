from pywb.rewrite.rewrite_live import get_rewritten
from pywb.rewrite.url_rewriter import UrlRewriter

from pywb import get_test_dir

# This module has some rewriting tests against the 'live web'
# As such, the content may change and the test may break

urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html', '/pywb/')


def test_local_1():
    status_headers, buff = get_rewritten(get_test_dir() + 'text_content/sample.html', urlrewriter, 'com,example,test)/')

    # wombat insert added
    assert '<head><script src="/static/default/wombat.js"> </script>' in buff

    # location rewritten
    assert 'window.WB_wombat_location = "/other.html"' in buff

    # link rewritten
    assert '"/pywb/20131226101010/http://example.com/some/path/another.html"' in buff


def test_local_2_no_js_location_rewrite():
    status_headers, buff = get_rewritten(get_test_dir() + 'text_content/sample.html', urlrewriter, 'example,example,test)/nolocation_rewrite')

    # no wombat insert
    assert '<head><script src="/static/default/wombat.js"> </script>' not in buff

    # no location rewrite
    assert 'window.location = "/other.html"' in buff

    # still link rewrite
    assert '"/pywb/20131226101010/http://example.com/some/path/another.html"' in buff

def test_example_1():
    status_headers, buff = get_rewritten('http://example.com/', urlrewriter)

    # verify header rewriting
    assert (('X-Archive-Orig-connection', 'close') in status_headers.headers), status_headers


def test_example_2():
    status_headers, buff = get_rewritten('http://example.com/', urlrewriter)

    # verify header rewriting
    assert (('X-Archive-Orig-connection', 'close') in status_headers.headers), status_headers

    assert '/pywb/20131226101010/http://www.iana.org/domains/example' in buff, buff



def test_example_domain_specific_3():
    status_headers, buff = get_rewritten('http://facebook.com/digitalpreservation', urlrewriter)

    # comment out bootloader
    assert '/* Bootloader.configurePage' in buff, buff


