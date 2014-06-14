"""
Fetch a url from live web and apply rewriting rules
"""

import requests
import datetime
import mimetypes

from urlparse import urlsplit

from pywb.utils.loaders import is_http, LimitReader
from pywb.utils.timeutils import datetime_to_timestamp
from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.canonicalize import canonicalize

from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.rewrite_content import RewriteContent


#=================================================================
class LiveRewriter(object):
    PROXY_HEADER_LIST = [('HTTP_USER_AGENT', 'User-Agent'),
                         ('HTTP_ACCEPT', 'Accept'),
                         ('HTTP_ACCEPT_LANGUAGE', 'Accept-Language'),
                         ('HTTP_ACCEPT_CHARSET', 'Accept-Charset'),
                         ('HTTP_ACCEPT_ENCODING', 'Accept-Encoding'),
                         ('HTTP_RANGE', 'Range'),
                         ('HTTP_CACHE_CONTROL', 'Cache-Control'),
                         ('HTTP_X_REQUESTED_WITH', 'X-Requested-With'),
                         ('HTTP_X_CSRF_TOKEN', 'X-CSRF-Token'),
                         ('HTTP_PE_TOKEN', 'PE-Token'),
                         ('HTTP_COOKIE', 'Cookie'),
                         ('CONTENT_TYPE', 'Content-Type'),
                         ('CONTENT_LENGTH', 'Content-Length'),
                         ('REL_REFERER', 'Referer'),
                        ]

    def __init__(self, defmod=''):
        self.rewriter = RewriteContent(defmod=defmod)

    def fetch_local_file(self, uri):
        fh = open(uri)

        content_type, _ = mimetypes.guess_type(uri)

        # create fake headers for local file
        status_headers = StatusAndHeaders('200 OK',
                                          [('Content-Type', content_type)])
        stream = fh

        return (status_headers, stream)

    def translate_headers(self, url, env):
        headers = {}

        splits = urlsplit(url)

        for name, value in env.iteritems():
            if name == 'HTTP_HOST':
                name = 'Host'
                value = splits.netloc

            elif name == 'HTTP_ORIGIN':
                name = 'Origin'
                value = (splits.scheme + '://' + splits.netloc)

            elif name.startswith('HTTP_'):
                name = name[5:].title().replace('_', '-')

            elif name in ('CONTENT_LENGTH', 'CONTENT_TYPE'):
                name = name.title().replace('_', '-')

            elif name == 'REL_REFERER':
                name = 'Referer'
            else:
                continue

            if value:
                headers[name] = value

        return headers

    def fetch_http(self, url,
                   env=None,
                   req_headers={},
                   follow_redirects=False,
                   proxies=None):

        method = 'GET'
        data = None

        if env is not None:
            method = env['REQUEST_METHOD'].upper()
            input_ = env['wsgi.input']

            req_headers.update(self.translate_headers(url, env))

            if method in ('POST', 'PUT'):
                len_ = env.get('CONTENT_LENGTH')
                if len_:
                    data = LimitReader(input_, int(len_))
                else:
                    data = input_

        response = requests.request(method=method,
                                    url=url,
                                    data=data,
                                    headers=req_headers,
                                    allow_redirects=follow_redirects,
                                    proxies=proxies,
                                    stream=True,
                                    verify=False)

        statusline = str(response.status_code) + ' ' + response.reason

        headers = response.headers.items()
        stream = response.raw

        status_headers = StatusAndHeaders(statusline, headers)

        return (status_headers, stream)

    def fetch_request(self, url, urlrewriter,
                      head_insert_func=None,
                      urlkey=None,
                      env=None,
                      req_headers={},
                      timestamp=None,
                      follow_redirects=False,
                      proxies=None,
                      mod=None):

        ts_err = url.split('///')

        if len(ts_err) > 1:
            url = 'http://' + ts_err[1]

        if url.startswith('//'):
            url = 'http:' + url

        if is_http(url):
            (status_headers, stream) = self.fetch_http(url, env, req_headers,
                                                       follow_redirects,
                                                       proxies)
        else:
            (status_headers, stream) = self.fetch_local_file(url)

        # explicit urlkey may be passed in (say for testing)
        if not urlkey:
            urlkey = canonicalize(url)

        if timestamp is None:
            timestamp = datetime_to_timestamp(datetime.datetime.utcnow())

        cdx = {'urlkey': urlkey,
               'timestamp': timestamp,
               'original': url,
               'statuscode': status_headers.get_statuscode(),
               'mimetype': status_headers.get_header('Content-Type')
              }

        result = (self.rewriter.
                  rewrite_content(urlrewriter,
                                  status_headers,
                                  stream,
                                  head_insert_func=head_insert_func,
                                  urlkey=urlkey,
                                  cdx=cdx,
                                  mod=mod))

        return result

    def get_rewritten(self, *args, **kwargs):

        result = self.fetch_request(*args, **kwargs)

        status_headers, gen, is_rewritten = result

        buff = ''.join(gen)

        return (status_headers, buff)


#=================================================================
def main():  # pragma: no cover
    import sys

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

    liverewriter = LiveRewriter()

    status_headers, buff = liverewriter.get_rewritten(url, urlrewriter)

    sys.stdout.write(buff)
    return 0


#=================================================================
if __name__ == "__main__":
    exit(main())
