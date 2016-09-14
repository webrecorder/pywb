from six.moves.urllib.parse import urljoin, urlsplit, urlunsplit

from pywb.rewrite.wburl import WbUrl
from pywb.rewrite.cookie_rewriter import get_cookie_rewriter


#=================================================================
class UrlRewriter(object):
    """
    Main pywb UrlRewriter which rewrites absolute and relative urls
    to be relative to the current page, as specified via a WbUrl
    instance and an optional full path prefix
    """

    NO_REWRITE_URI_PREFIX = ('#', 'javascript:', 'data:',
                             'mailto:', 'about:', 'file:', '{')

    PROTOCOLS = ('http:', 'https:', 'ftp:', 'mms:', 'rtsp:', 'wais:')

    REL_SCHEME = ('//', r'\/\/', r'\\/\\/')

    PARENT_PATH = '../'
    REL_PATH = '/'

    def __init__(self, wburl, prefix='', full_prefix=None, rel_prefix=None,
                 root_path=None, cookie_scope=None, rewrite_opts=None):
        self.wburl = wburl if isinstance(wburl, WbUrl) else WbUrl(wburl)
        self.prefix = prefix
        self.full_prefix = full_prefix or prefix
        self.rel_prefix = rel_prefix or prefix
        self.root_path = root_path or '/'
        if self.full_prefix and self.full_prefix.startswith(self.PROTOCOLS):
            self.prefix_scheme = self.full_prefix.split(':')[0]
        else:
            self.prefix_scheme = None
        self.prefix_abs = self.prefix and self.prefix.startswith(self.PROTOCOLS)
        self.cookie_scope = cookie_scope
        self.rewrite_opts = rewrite_opts or {}

        if self.rewrite_opts.get('punycode_links'):
            self.wburl._do_percent_encode = False

    def rewrite(self, url, mod=None):
        # if special protocol, no rewriting at all
        if url.startswith(self.NO_REWRITE_URI_PREFIX):
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

        is_abs = url.startswith(self.PROTOCOLS)

        scheme_rel = False
        if url.startswith(self.REL_SCHEME):
            is_abs = True
            scheme_rel = True
        elif (not is_abs and
              not url.startswith(self.REL_PATH) and
              self.PARENT_PATH not in url):
            return url

            # if prefix starts with a scheme
            #if self.prefix_scheme:
            #    url = self.prefix_scheme + ':' + url
            #url = 'http:' + url

        # optimize: join if not absolute url, otherwise just use as is
        if not is_abs:
            new_url = self.urljoin(wburl.url, url)
        else:
            new_url = url

        if mod is None:
            mod = wburl.mod

        final_url = self.prefix + wburl.to_str(mod=mod, url=new_url)

        if not is_abs and self.prefix_abs and not self.rewrite_opts.get('no_match_rel'):
            parts = final_url.split('/', 3)
            final_url = '/'
            if len(parts) == 4:
                final_url += parts[3]

        # experiment for setting scheme rel url
        elif scheme_rel and self.prefix_abs:
            final_url = final_url.split(':', 1)[1]

        return final_url

    def get_new_url(self, **kwargs):
        return self.prefix + self.wburl.to_str(**kwargs)

    def rebase_rewriter(self, new_url):
        if new_url.startswith(self.prefix):
            new_url = new_url[len(self.prefix):]
        elif new_url.startswith(self.rel_prefix):
            new_url = new_url[len(self.rel_prefix):]

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
    def urljoin(orig_url, url):  # pragma: no cover
        new_url = urljoin(orig_url, url)
        if '../' not in new_url:
            return new_url

        # only needed in py2 as py3 urljoin resolves '../'
        parts = urlsplit(new_url)
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

        new_url = urlunsplit(parts)
        return new_url


#=================================================================
class SchemeOnlyUrlRewriter(UrlRewriter):
    """
    A url rewriter which ensures that any urls have the same
    scheme (http or https) as the base url.
    Other urls/input is unchanged.
    """

    def __init__(self, *args, **kwargs):
        super(SchemeOnlyUrlRewriter, self).__init__(*args, **kwargs)
        self.url_scheme = self.wburl.url.split(':')[0]
        if self.url_scheme == 'https':
            self.opposite_scheme = 'http'
        else:
            self.opposite_scheme = 'https'

    def rewrite(self, url, mod=None):
        if url.startswith(self.opposite_scheme + '://'):
            url = self.url_scheme + url[len(self.opposite_scheme):]

        return url

    def get_new_url(self, **kwargs):
        return kwargs.get('url', self.wburl.url)

    def rebase_rewriter(self, new_url):
        return self

    def get_cookie_rewriter(self, scope=None):
        return None

    def deprefix_url(self):
        return self.wburl.url
