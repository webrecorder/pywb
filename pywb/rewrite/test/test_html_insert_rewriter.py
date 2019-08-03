


r'''
>>> parse('<html><head><some-tag></head</html>')
'<html><head><!--Insert--><some-tag></head</html>'

>>> parse('<HTML><A Href="page.html">Text</a></hTmL>')
'<HTML><!--Insert--><A Href="page.html">Text</a></hTmL>'

>>> parse('<html>   <  head>  <link>')
'<html>   <  head>  <!--Insert--><link>'

>>> parse('<  head>  <link> <html>')
'<  head>  <!--Insert--><link> <html>'

>>> parse('<head></head>text')
'<head></head>text<!--Insert-->'
'''

from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.html_insert_rewriter import HTMLInsertOnlyRewriter

def parse(html_text):
    urlrewriter = UrlRewriter('20131226101010/https://example.com/some/path.html', '/web/')

    rewriter = HTMLInsertOnlyRewriter(urlrewriter, head_insert='<!--Insert-->')

    return rewriter.rewrite(html_text) + rewriter.final_read()

