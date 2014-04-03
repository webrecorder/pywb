"""
Fetch a url from live web and apply rewriting rules
"""

import urllib2
import os
import sys
import datetime
import mimetypes

from pywb.utils.loaders import is_http
from pywb.utils.timeutils import datetime_to_timestamp
from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.canonicalize import canonicalize

from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.rewrite_content import RewriteContent


#=================================================================
def get_status_and_stream(url):
    resp = urllib2.urlopen(url)

    headers = []
    for name, value in resp.info().dict.iteritems():
        headers.append((name, value))

    status_headers = StatusAndHeaders('200 OK', headers)
    stream = resp

    return (status_headers, stream)


#=================================================================
def get_local_file(uri):
    fh = open(uri)

    content_type, _ = mimetypes.guess_type(uri)

    # create fake headers for local file
    status_headers = StatusAndHeaders('200 OK',
                                      [('Content-Type', content_type)])
    stream = fh

    return (status_headers, stream)


#=================================================================
def get_rewritten(url, urlrewriter, urlkey=None, head_insert_func=None):
    if is_http(url):
        (status_headers, stream) = get_status_and_stream(url)
    else:
        (status_headers, stream) = get_local_file(url)

    # explicit urlkey may be passed in (say for testing)
    if not urlkey:
        urlkey = canonicalize(url)

    rewriter = RewriteContent()

    result = rewriter.rewrite_content(urlrewriter,
                                      status_headers,
                                      stream,
                                      head_insert_func=head_insert_func,
                                      urlkey=urlkey)

    status_headers, gen, is_rewritten = result

    buff = ''.join(gen)

    return (status_headers, buff)


#=================================================================
def main():  # pragma: no cover
    if len(sys.argv) < 2:
        msg = 'Usage: {0} url-to-fetch [wb-url-target] [extra-prefix]'
        print msg.format(sys.argv[0])
        return 1
    else:
        url = sys.argv[1]

    if len(sys.argv) >= 3:
        wburl_str = sys.argv[2]
        if wburl_str.startswith('/'):
            wburl_str = wburl_str[1:]

        prefix, wburl_str = wburl_str.split('/', 1)
        prefix = '/' + prefix + '/'
    else:
        wburl_str = (datetime_to_timestamp(datetime.datetime.now()) +
                     '/http://example.com/path/sample.html')
        prefix = '/pywb_rewrite/'

    urlrewriter = UrlRewriter(wburl_str, prefix)

    status_headers, buff = get_rewritten(url, urlrewriter)

    sys.stdout.write(buff)
    return 0


#=================================================================
if __name__ == "__main__":
    exit(main())
