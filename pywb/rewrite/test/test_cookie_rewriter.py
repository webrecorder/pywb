r"""
# No rewriting
>>> rewrite_cookie('a=b; c=d;')
[('Set-Cookie', 'a=b'), ('Set-Cookie', 'c=d')]

>>> rewrite_cookie('some=value; Domain=foo.com; Path=/;')
[('Set-Cookie', 'some=value; Path=/pywb/20131226101010/http://example.com/')]

>>> rewrite_cookie('some=value; Domain=foo.com; Path=/diff/path/;')
[('Set-Cookie', 'some=value; Path=/pywb/20131226101010/http://example.com/diff/path/')]

>>> rewrite_cookie('abc=def; Path=file.html; Expires=Wed, 13 Jan 2021 22:23:01 GMT')
[('Set-Cookie', 'abc=def; Path=/pywb/20131226101010/http://example.com/some/path/file.html')]

"""


from pywb.rewrite.cookie_rewriter import WbUrlCookieRewriter
from pywb.rewrite.url_rewriter import UrlRewriter

urlrewriter = UrlRewriter('20131226101010/http://example.com/some/path/index.html', '/pywb/')

def rewrite_cookie(cookie_str):
    return WbUrlCookieRewriter(urlrewriter).rewrite(cookie_str)

