import urlparse

from wburl import WbUrl
from cookie_rewriter import get_cookie_rewriter


#=================================================================
class UrlRewriter(object):
    """
    Main pywb UrlRewriter which rewrites absolute and relative urls
    to be relative to the current page, as specified via a WbUrl
    instance and an optional full path prefix
    """

    NO_REWRITE_URI_PREFIX = ['#', 'javascript:', 'data:',
                             'mailto:', 'about:', 'file:']

    PROTOCOLS = ['http:', 'https:', 'ftp:', 'mms:', 'rtsp:', 'wais:']

    REL_SCHEME = ('//', r'\/\/', r'\\/\\/')

    def __init__(self, wburl, prefix, full_prefix=None, rel_prefix=None,
                 root_path=None, cookie_scope=None, rewrite_opts={}):
        self.wburl = wburl if isinstance(wburl, WbUrl) else WbUrl(wburl)
        self.prefix = prefix
        self.full_prefix = full_prefix
        self.rel_prefix = rel_prefix if rel_prefix else prefix
        self.root_path = root_path if root_path else '/'
        self.cookie_scope = cookie_scope
        self.rewrite_opts = rewrite_opts

        if rewrite_opts.get('punycode_links'):
            self.wburl._do_percent_encode = False

    def rewrite(self, url, mod=None):
        # if special protocol, no rewriting at all
        if any(url.startswith(x) for x in self.NO_REWRITE_URI_PREFIX):
            return url

        if (self.prefix and
             self.prefix != '/' and
             url.startswith(self.prefix)):
            return url

        if (self.full_prefix and
             self.full_prefix != self.prefix and
             url.startswith(self.full_prefix)):
            return url

        wburl = self.wburl

        is_abs = any(url.startswith(x) for x in self.PROTOCOLS)

        if url.startswith(self.REL_SCHEME):
            is_abs = True
            url = 'http:' + url

        # Optimized rewriter for
        # -rel urls that don't start with / and
        # do not contain ../ and no special mod
        if not (is_abs or mod or url.startswith('/') or ('../' in url)):
            final_url = urlparse.urljoin(self.prefix + wburl.original_url, url)

        else:
            # optimize: join if not absolute url, otherwise just use that
            if not is_abs:
                new_url = self.urljoin(wburl.url, url)
            else:
                new_url = url

            if mod is None:
                mod = wburl.mod

            final_url = self.prefix + wburl.to_str(mod=mod,
                                                   url=new_url)
        return final_url

    def get_new_url(self, **kwargs):
        return self.prefix + self.wburl.to_str(**kwargs)

    def rebase_rewriter(self, new_url):
        if new_url.startswith(self.prefix):
            new_url = new_url[len(self.prefix):]

        new_wburl = WbUrl(new_url)
        return self._create_rebased_rewriter(new_wburl, self.prefix)

    def _create_rebased_rewriter(self, new_wburl, prefix):
        return UrlRewriter(new_wburl, prefix)

    def get_cookie_rewriter(self, scope=None):
        # collection scope overrides rule scope?
        if self.cookie_scope:
            scope = self.cookie_scope

        cls = get_cookie_rewriter(scope)
        return cls(self)

    def deprefix_url(self):
        return self.wburl.deprefix_url(self.full_prefix)

    def __repr__(self):
        return "UrlRewriter('{0}', '{1}')".format(self.wburl, self.prefix)

    @staticmethod
    def urljoin(orig_url, url):
        new_url = urlparse.urljoin(orig_url, url)
        if '../' not in new_url:
            return new_url

        parts = urlparse.urlsplit(new_url)
        scheme, netloc, path, query, frag = parts

        path_parts = path.split('/')
        i = 0
        n = len(path_parts) - 1
        while i < n:
            if path_parts[i] == '..':
                del path_parts[i]
                n -= 1
                if i > 0:
                    del path_parts[i - 1]
                    n -= 1
                    i -= 1
            else:
                i += 1

        if path_parts == ['']:
            path = '/'
        else:
            path = '/'.join(path_parts)

        parts = (scheme, netloc, path, query, frag)

        new_url = urlparse.urlunsplit(parts)
        return new_url


#=================================================================
class HttpsUrlRewriter(UrlRewriter):
    """
    A url rewriter which urls that start with https:// to http://
    Other urls/input is unchanged.
    """

    HTTP = 'http://'
    HTTPS = 'https://'

    def rewrite(self, url, mod=None):
        return self.remove_https(url)

    def get_new_url(self, **kwargs):
        return kwargs.get('url', self.wburl.url)

    def rebase_rewriter(self, new_url):
        return self

    def get_cookie_rewriter(self, scope=None):
        return None

    def deprefix_url(self):
        return self.wburl.url

    @staticmethod
    def remove_https(url):
        rw = HttpsUrlRewriter
        if url.startswith(rw.HTTPS):
            result = rw.HTTP + url[len(rw.HTTPS):]
            return result
        else:
            return url
