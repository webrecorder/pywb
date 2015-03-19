"""
Fetch a url from live web and apply rewriting rules
"""

import requests
import mimetypes
import logging
import os

from urlparse import urlsplit

from pywb.utils.loaders import is_http, LimitReader, BlockLoader, to_file_url
from pywb.utils.loaders import extract_client_cookie
from pywb.utils.timeutils import timestamp_now
from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.canonicalize import canonicalize

from rewrite_content import RewriteContent


#=================================================================
class LiveRewriter(object):
    def __init__(self, is_framed_replay=False, proxies=None):
        self.rewriter = RewriteContent(is_framed_replay=is_framed_replay)

        self.proxies = proxies

        if self.proxies:
            logging.debug('Live Rewrite via proxy ' + str(proxies))

            if isinstance(proxies, str):
                self.proxies = {'http': proxies,
                                'https': proxies}

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

    def translate_headers(self, url, urlkey, env):
        headers = {}

        splits = urlsplit(url)
        has_cookies = False

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

            elif name == 'HTTP_REFERER':
                continue

            elif name == 'HTTP_X_FORWARDED_PROTO':
                name = 'X-Forwarded-Proto'
                value = splits.scheme

            elif name == 'HTTP_COOKIE':
                name = 'Cookie'
                value = self._req_cookie_rewrite(urlkey, value)
                has_cookies = True

            elif name.startswith('HTTP_'):
                name = name[5:].title().replace('_', '-')

            elif name in ('CONTENT_LENGTH', 'CONTENT_TYPE'):
                name = name.title().replace('_', '-')

            elif name == 'REL_REFERER':
                name = 'Referer'
            else:
                value = None

            if value:
                headers[name] = value

        if not has_cookies:
            value = self._req_cookie_rewrite(urlkey, '')
            if value:
                headers['Cookie'] = value

        return headers

    def _req_cookie_rewrite(self, urlkey, value):
        rule = self.rewriter.ruleset.get_first_match(urlkey)
        if not rule or not rule.req_cookie_rewrite:
            return value

        for cr in rule.req_cookie_rewrite:
            try:
                value = cr['rx'].sub(cr['replace'], value)
            except KeyError:
                pass

        return value

    def fetch_http(self, url,
                   urlkey=None,
                   env=None,
                   req_headers=None,
                   follow_redirects=False,
                   ignore_proxies=False,
                   verify=True):

        method = 'GET'
        data = None

        proxies = None
        if not ignore_proxies:
            proxies = self.proxies

        if not req_headers:
            req_headers = {}

        if env is not None:
            method = env['REQUEST_METHOD'].upper()
            input_ = env['wsgi.input']

            req_headers.update(self.translate_headers(url, urlkey, env))

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
                                    verify=verify)

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
                      ignore_proxies=False,
                      verify=True):

        ts_err = url.split('///')

        # fixup for accidental erroneous rewrite which has ///
        # (unless file:///)
        if len(ts_err) > 1 and ts_err[0] != 'file:':
            url = 'http://' + ts_err[1]

        if url.startswith('//'):
            url = 'http:' + url

        if is_http(url):
            is_remote = True
        else:
            is_remote = False
            if not url.startswith('file:'):
                url = to_file_url(url)

        # explicit urlkey may be passed in (say for testing)
        if not urlkey:
            urlkey = canonicalize(url)

        if is_remote:
            (status_headers, stream) = self.fetch_http(url, urlkey, env,
                                                       req_headers,
                                                       follow_redirects,
                                                       ignore_proxies,
                                                       verify)
        else:
            (status_headers, stream) = self.fetch_local_file(url)

        if timestamp is None:
            timestamp = timestamp_now()

        cdx = {'urlkey': urlkey,
               'timestamp': timestamp,
               'url': url,
               'status': status_headers.get_statuscode(),
               'mime': status_headers.get_header('Content-Type'),
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
