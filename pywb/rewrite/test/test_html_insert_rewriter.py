


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

>>> parse('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<html xmlns="http://www.w3.org/1999/xhtml"><body></body></html>')
'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<html xmlns="http://www.w3.org/1999/xhtml"><!--Insert--><body></body></html>'

# ajax leave unchanged?
>>> parse('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<html xmlns="http://www.w3.org/1999/xhtml"><body></body></html>', is_ajax=True)
'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<html xmlns="http://www.w3.org/1999/xhtml"><body></body></html>'
'''

from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.html_insert_rewriter import HTMLInsertOnlyRewriter

def parse(html_text, is_ajax=False):
    urlrewriter = UrlRewriter('20131226101010/https://example.com/some/path.html', '/web/')

    if is_ajax:
        urlrewriter.rewrite_opts['is_ajax'] = True

    rewriter = HTMLInsertOnlyRewriter(urlrewriter, head_insert='<!--Insert-->')

    return rewriter.rewrite(html_text) + rewriter.final_read()

