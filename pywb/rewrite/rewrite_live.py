"""
Fetch a url from live web and apply rewriting rules
"""

import requests
import datetime
import mimetypes
import logging

from urlparse import urlsplit

from pywb.utils.loaders import is_http, LimitReader, BlockLoader
from pywb.utils.loaders import extract_client_cookie
from pywb.utils.timeutils import datetime_to_timestamp
from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.canonicalize import canonicalize

from url_rewriter import UrlRewriter
from wburl import WbUrl
from rewrite_content import RewriteContent


#=================================================================
class LiveRewriter(object):
    def __init__(self, is_framed_replay=False, default_proxy=None):
        self.rewriter = RewriteContent(is_framed_replay=is_framed_replay)
        self.default_proxy = default_proxy
        if self.default_proxy:
            logging.debug('Live Rewrite via proxy ' + self.default_proxy)
        else:
            logging.debug('Live Rewrite Direct (no proxy)')

    def fetch_local_file(self, uri):
        #fh = open(uri)
        fh = BlockLoader().load_file_or_resource(uri)

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

            elif name == 'HTTP_X_CSRFTOKEN':
                name = 'X-CSRFToken'
                cookie_val = extract_client_cookie(env, 'csrftoken')
                if cookie_val:
                    value = cookie_val

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
                   req_headers=None,
                   follow_redirects=False,
                   proxies=None):

        method = 'GET'
        data = None

        if not proxies and self.default_proxy:
            proxies = {'http': self.default_proxy,
                       'https': self.default_proxy}

        if not req_headers:
            req_headers = {}

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
                      proxies=None):

        ts_err = url.split('///')

        # fixup for accidental erroneous rewrite which has ///
        # (unless file:///)
        if len(ts_err) > 1 and ts_err[0] != 'file:':
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
               'mimetype': status_headers.get_header('Content-Type'),
               'is_live': True,
              }

        result = (self.rewriter.
                  rewrite_content(urlrewriter,
                                  status_headers,
                                  stream,
                                  head_insert_func=head_insert_func,
                                  urlkey=urlkey,
                                  cdx=cdx))

        if env:
            env['pywb.cdx'] = cdx

        return result

    def get_rewritten(self, *args, **kwargs):
        result = self.fetch_request(*args, **kwargs)

        status_headers, gen, is_rewritten = result

        buff = ''.join(gen)

        return (status_headers, buff)
