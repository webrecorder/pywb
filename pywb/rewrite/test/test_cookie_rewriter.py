r"""
# Default -- MinimalScopeRewriter
# No rewriting
>>> rewrite_cookie('a=b; c=d;')
[('Set-Cookie', 'a=b'), ('Set-Cookie', 'c=d')]

>>> rewrite_cookie('some=value; Path=/;')
[('Set-Cookie', 'some=value; Path=/pywb/20131226101010/http://example.com/')]

>>> rewrite_cookie('some=value; Path=../;', rewriter=urlrewriter2)
[('Set-Cookie', 'some=value; Path=/preview/em_/http://example.com/')]

>>> rewrite_cookie('some=value; Path=/diff/path/;')
[('Set-Cookie', 'some=value; Path=/pywb/20131226101010/http://example.com/diff/path/')]

# if domain set, set path to root
>>> rewrite_cookie('some=value; Domain=.example.com; Path=/diff/path/; Max-Age=1500')
[('Set-Cookie', 'some=value; Path=/pywb/')]

>>> rewrite_cookie('abc=def; Path=file.html; Expires=Wed, 13 Jan 2021 22:23:01 GMT')
[('Set-Cookie', 'abc=def; Path=/pywb/20131226101010/http://example.com/some/path/file.html')]

# Cookie with invalid chars, not parsed
>>> rewrite_cookie('abc@def=123')
[]


# ExactCookieRewriter -- always removes Path and Domain
>>> rewrite_cookie('some=value; Path=/diff/path/;', urlrewriter, 'exact')
[('Set-Cookie', 'some=value')]

>>> rewrite_cookie('some=value; Domain=.example.com; Path=/diff/path/; Max-Age=1500', urlrewriter, 'exact')
[('Set-Cookie', 'some=value')]


# RootCookieRewriter -- always sets Path=/, removes Domain
>>> rewrite_cookie('some=value; Path=/diff/path/;', urlrewriter, 'root')
[('Set-Cookie', 'some=value; Path=/')]

>>> rewrite_cookie('some=value; Domain=.example.com; Path=/diff/path/; Max-Age=1500', urlrewriter, 'root')
[('Set-Cookie', 'some=value; Path=/')]



"""


from pywb.rewrite.cookie_rewriter import MinimalScopeCookieRewriter, get_cookie_rewriter
from pywb.rewrite.url_rewriter import UrlRewriter

urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html', '/pywb/')

urlrewriter2 = UrlRewriter('em_/http://example.com/', '/preview/')


def rewrite_cookie(cookie_str, rewriter=urlrewriter, scope='default'):
    cookie_rewriter = get_cookie_rewriter(scope)
    return cookie_rewriter(rewriter).rewrite(cookie_str)

