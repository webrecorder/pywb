r"""
# Default -- MinimalScopeRewriter (Collection scope)
# No rewriting
>>> x = rewrite_cookie('a=b; c=d;')
>>> ('Set-Cookie', 'a=b') in x
True

>>> ('Set-Cookie', 'c=d') in x
True

>>> rewrite_cookie('some=value; Path=/;', urlrewriter, 'coll')
[('Set-Cookie', 'some=value; Path=/pywb/20131226101010/http://example.com/')]

>>> rewrite_cookie('some=value; Path=../;', urlrewriter2, 'coll')
[('Set-Cookie', 'some=value; Path=/preview/em_/http://example.com/')]

>>> rewrite_cookie('some=value; Path=/diff/path/;', urlrewriter, 'coll')
[('Set-Cookie', 'some=value; Path=/pywb/20131226101010/http://example.com/diff/path/')]

# if domain set, set path to root
>>> rewrite_cookie('some=value; Domain=.example.com; Path=/diff/path/; Max-Age=1500', urlrewriter, 'coll')
[('Set-Cookie', 'some=value; Path=/pywb/')]

>>> rewrite_cookie('abc=def; Path=file.html; Expires=Wed, 13 Jan 2021 22:23:01 GMT', urlrewriter, 'coll')
[('Set-Cookie', 'abc=def; Path=file.html')]

# keep Max-Age
>>> rewrite_cookie('abc=def; Path=/file.html; Max-Age=1500', urlrewriter2, 'coll')
[('Set-Cookie', 'abc=def; Max-Age=1500; Path=/preview/em_/http://example.com/file.html')]

# Cookie with invalid chars, not parsed
>>> rewrite_cookie('abc@def=123', urlrewriter, 'coll')
[]


# ExactCookieRewriter -- always removes Path and Domain
>>> rewrite_cookie('some=value; Path=/diff/path/;', urlrewriter, 'exact')
[('Set-Cookie', 'some=value')]

>>> rewrite_cookie('some=value; Domain=.example.com; Path=/diff/path/; Max-Age=1500', urlrewriter, 'exact')
[('Set-Cookie', 'some=value')]


# HostCookieRewriter -- set path to host
>>> rewrite_cookie('some=value; Path=/diff/path/', urlrewriter, 'host')
[('Set-Cookie', 'some=value; Path=/pywb/20131226101010/http://example.com/diff/path/')]

>>> rewrite_cookie('some=value; Domain=.example.com; Path=/diff/path/; Max-Age=1500', urlrewriter, 'host')
[('Set-Cookie', 'some=value; Path=/pywb/20131226101010/http://example.com/')]

# Disable for now as it 2.6 doesn't include HttpOnly and Secure

# RootCookieRewriter -- always sets Path=/, removes Domain
>>> rewrite_cookie('some=value; Path=/diff/path/;', urlrewriter, 'root')
[('Set-Cookie', 'some=value; Path=/')]

>>> rewrite_cookie('some=value; Domain=.example.com; Path=/diff/path/; Max-Age=1500', urlrewriter, 'root')
[('Set-Cookie', 'some=value; Path=/')]

# RemoveAllCookiesRewriter -- remove all cookies
>>> rewrite_cookie('some=value; Path=/diff/path/;', urlrewriter, 'removeall')
[]

>>> rewrite_cookie('some=value; Domain=.example.com; Path=/diff/path/; Max-Age=1500', urlrewriter, 'removeall')
[]


"""


from pywb.rewrite.cookie_rewriter import MinimalScopeCookieRewriter
from pywb.rewrite.cookie_rewriter import get_cookie_rewriter
from pywb.rewrite.url_rewriter import UrlRewriter
import pytest
import sys

urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html',
                          'http://localhost:8080/pywb/',
                          rel_prefix='/pywb/')

urlrewriter2 = UrlRewriter('em_/http://example.com/', '/preview/')
urlrewriter2.rewrite_opts['is_live'] = True

urlrewriter3 = UrlRewriter('em_/http://example.com/', 'https://localhost:8080/preview/')


def rewrite_cookie(cookie_str, rewriter=urlrewriter, scope='default'):
    cookie_rewriter = get_cookie_rewriter(scope)
    return cookie_rewriter(rewriter).rewrite(cookie_str)


# ============================================================================
@pytest.mark.skipif(sys.version_info < (2,7), reason='Unsupported')
class TestCookies(object):
    def test_remove_expires(self):
        res = rewrite_cookie('abc=def; Path=/file.html; Expires=Wed, 13 Jan 2021 22:23:01 GMT', urlrewriter2, 'coll')
        assert len(res) == 1
        assert res[0][1].lower() == 'abc=def; path=/preview/em_/http://example.com/file.html'

    def test_remove_expires_2(self):
        res = rewrite_cookie('abc=def; Path=/file.html; Expires=Wed, 13 Jan 2021 22:23:01 UTC', urlrewriter2, 'coll')
        assert len(res) == 1
        assert res[0][1].lower() == 'abc=def; path=/preview/em_/http://example.com/file.html'

    def test_remove_expires_3(self):
        res = rewrite_cookie('abc=def; Path=/file.html; Expires=Wed, 13 Jan 2021 22:23:01 GMT; httponly; Max-Age=100', urlrewriter2, 'coll')
        assert len(res) == 1
        assert res[0][1].lower() == 'abc=def; httponly; max-age=100; path=/preview/em_/http://example.com/file.html'

    def test_remove_expires_4(self):
        res = rewrite_cookie('abc=def; Path=/file.html; Expires=Wed, 13 Jan 2021 22:23:01 GMT, foo=bar', urlrewriter2, 'coll')
        assert len(res) == 2
        res = sorted(res)
        assert res[0][1].lower() == 'abc=def; path=/preview/em_/http://example.com/file.html,'
        assert res[1][1].lower() == 'foo=bar'

    def test_http_secure_flag(self):
        res = rewrite_cookie('some=value; Domain=.example.com; Secure; Path=/diff/path/; HttpOnly; Max-Age=1500', urlrewriter, 'host')
        assert len(res) == 1
        assert res[0][1].lower() == 'some=value; httponly; path=/pywb/20131226101010/http://example.com/'

    def test_secure_flag_remove(self):
        # Secure Remove
        res = rewrite_cookie('abc=def; Path=/file.html; HttpOnly; Secure', urlrewriter2, 'coll')
        assert len(res) == 1
        assert res[0][1].lower() == 'abc=def; httponly; path=/preview/em_/http://example.com/file.html'

    def test_secure_flag_keep(self):
        # Secure Keep
        res = rewrite_cookie('abc=def; Path=/file.html; HttpOnly; Secure', urlrewriter3, 'coll')
        assert res[0][1].lower() == 'abc=def; httponly; path=/preview/em_/http://example.com/file.html; secure'


