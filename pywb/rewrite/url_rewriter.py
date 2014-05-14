import copy
import urlparse

from wburl import WbUrl
from cookie_rewriter import WbUrlCookieRewriter


#=================================================================
class UrlRewriter(object):
    """
    Main pywb UrlRewriter which rewrites absolute and relative urls
    to be relative to the current page, as specified via a WbUrl
    instance and an optional full path prefix
    """

    NO_REWRITE_URI_PREFIX = ['#', 'javascript:', 'data:', 'mailto:', 'about:']

    PROTOCOLS = ['http:', 'https:', 'ftp:', 'mms:', 'rtsp:', 'wais:']

    def __init__(self, wburl, prefix, full_prefix=None):
        self.wburl = wburl if isinstance(wburl, WbUrl) else WbUrl(wburl)
        self.prefix = prefix
        self.full_prefix = full_prefix

        #if self.prefix.endswith('/'):
        #    self.prefix = self.prefix[:-1]

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

        if url.startswith('//'):
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
                new_url = urlparse.urljoin(wburl.url, url).replace('../', '')
            else:
                new_url = url

            if mod is None:
                mod = wburl.mod

            final_url = self.prefix + wburl.to_str(mod=mod, url=new_url)

        return final_url

    def get_abs_url(self, url=''):
        return self.prefix + self.wburl.to_str(url=url)

    def get_timestamp_url(self, timestamp, url=None):
        if url is None:
            url = self.wburl.url

        return self.prefix + self.wburl.to_str(timestamp=timestamp, url=url)

    def rebase_rewriter(self, new_url):
        #self.wburl.url = newUrl
        new_wburl = copy.copy(self.wburl)
        new_wburl.url = new_url
        return UrlRewriter(new_wburl, self.prefix)

    def get_cookie_rewriter(self):
        return WbUrlCookieRewriter(self)

    def __repr__(self):
        return "UrlRewriter('{0}', '{1}')".format(self.wburl, self.prefix)


#=================================================================
class HttpsUrlRewriter(object):
    """
    A url rewriter which urls that start with https:// to http://
    Other urls/input is unchanged.
    """

    HTTP = 'http://'
    HTTPS = 'https://'

    def __init__(self, wburl, prefix, full_prefix=None):
        pass

    def rewrite(self, url, mod=None):
        if url.startswith(self.HTTPS):
            result = self.HTTP + url[len(self.HTTPS):]
            return result
        else:
            return url

    def get_timestamp_url(self, timestamp, url):
        return url

    def get_abs_url(self, url=''):
        return url

    def rebase_rewriter(self, new_url):
        return self

    def get_cookie_rewriter(self):
        return None
