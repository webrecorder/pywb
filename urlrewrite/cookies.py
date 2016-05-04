from pywb.rewrite.cookie_rewriter import WbUrlBaseCookieRewriter
from pywb.utils.timeutils import datetime_to_http_date
from six.moves.http_cookiejar import CookieJar, DefaultCookiePolicy

import redis

import tldextract
import time
import datetime
import six


# =============================================================================
class CookieTracker(object):
    def __init__(self, redis):
        self.redis = redis

    def get_rewriter(self, url_rewriter, cookie_key):
        return DomainCacheCookieRewriter(url_rewriter,
                                         self.redis,
                                         cookie_key)

    def get_cookie_headers(self, url, cookie_key):
        subds = self.get_subdomains(url)
        if not subds:
            return None, None

        with redis.utils.pipeline(self.redis) as pi:
            for x in subds:
                pi.hgetall(cookie_key + '.' + x)

            all_res = pi.execute()

        cookies = []
        set_cookies = []

        for res in all_res:
            if not res:
                continue

            for n, v in six.iteritems(res):
                n = n.decode('utf-8')
                v = v.decode('utf-8')
                full = n + '=' + v
                cookies.append(full.split(';')[0])
                set_cookies.append(('Set-Cookie', full + '; Max-Age=120'))

        cookies = ';'.join(cookies)
        return cookies, set_cookies

    @staticmethod
    def get_subdomains(url):
        tld = tldextract.extract(url)

        if not tld.subdomain:
            return None

        main = tld.domain + '.' + tld.suffix
        full = tld.subdomain + '.' + main

        def get_all_subdomains(main, full):
            doms = []
            while main != full:
                full = full.split('.', 1)[1]
                doms.append(full)

            return doms

        all_subs = get_all_subdomains(main, full)
        return all_subs


# =============================================================================
class DomainCacheCookieRewriter(WbUrlBaseCookieRewriter):
    def __init__(self, url_rewriter, redis, cookie_key):
        super(DomainCacheCookieRewriter, self).__init__(url_rewriter)
        self.redis = redis
        self.cookie_key = cookie_key

    def rewrite_cookie(self, name, morsel):
        # if domain set, no choice but to expand cookie path to root
        domain = morsel.pop('domain', '')

        if domain:
            #if morsel.get('max-age'):
            #    morsel['max-age'] = int(morsel['max-age'])

            #self.cookiejar.set_cookie(self.morsel_to_cookie(morsel))
            #print(morsel, self.cookie_key + domain)

            string = morsel.value
            if morsel.get('path'):
                string += '; Path=' + morsel.get('path')

            if morsel.get('httponly'):
                string += '; HttpOnly'

            if morsel.get('secure'):
                string += '; Secure'

            with redis.utils.pipeline(self.redis) as pi:
                pi.hset(self.cookie_key + domain, morsel.key, string)
                pi.expire(self.cookie_key + domain, 120)

        # else set cookie to rewritten path
        if morsel.get('path'):
            morsel['path'] = self.url_rewriter.rewrite(morsel['path'])

        return morsel

    def get_expire_sec(self, morsel):
        expires = None

        if morsel.get('max-age'):
            return int(morsel['max-age'])

        expires = morsel.get('expires')
        if not expires:
            return None

        expires = expires.replace(' UTC', ' GMT')

        try:
            expires = time.strptime(expires, '%a, %d-%b-%Y %H:%M:%S GMT')
        except:
            pass

        try:
            expires = time.strptime(expires, '%a, %d %b %Y %H:%M:%S GMT')
        except:
            pass

        expires = time.mktime(expires)
        expires = expires - time.timezone - time.time()
        return expires


# ============================================================================

