"""
Fetch a url from live web and apply rewriting rules
"""

import requests
import datetime
import mimetypes

from pywb.utils.loaders import is_http
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

    def translate_headers(self, env, header_list=None):
        headers = {}

        if not header_list:
            header_list = self.PROXY_HEADER_LIST

        for env_name, req_name in header_list:
            value = env.get(env_name)
            if value is not None:
                headers[req_name] = value

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

            req_headers.update(self.translate_headers(env))

            if method in ('POST', 'PUT'):
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
                      proxies=None):

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
                                  cdx=cdx))

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
