from Cookie import SimpleCookie, CookieError


#=================================================================
class WbUrlCookieRewriter(object):
    """ Cookie rewriter for wburl-based requests
    Remove the domain and rewrite path, if any, to match
    given WbUrl using the url rewriter.
    """
    def __init__(self, url_rewriter):
        self.url_rewriter = url_rewriter

    def rewrite(self, cookie_str, header='Set-Cookie'):
        results = []
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_str)
        except CookieError:
            return results

        for name, morsel in cookie.iteritems():
            # if domain set, no choice but to expand cookie path to root
            if morsel.get('domain'):
                del morsel['domain']
                morsel['path'] = self.url_rewriter.prefix
            # else set cookie to rewritten path
            elif morsel.get('path'):
                morsel['path'] = self.url_rewriter.rewrite(morsel['path'])
            # remove expires as it refers to archived time
            if morsel.get('expires'):
                del morsel['expires']

            results.append((header, morsel.OutputString()))

        return results
