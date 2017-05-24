from pywb.rewrite.cookie_rewriter import WbUrlBaseCookieRewriter, HostScopeCookieRewriter
from warcio.timeutils import datetime_to_http_date
from six.moves import zip

import redis

import tldextract
import time
import datetime
import six


# =============================================================================
class CookieTracker(object):
    def __init__(self, redis, expire_time=120):
        self.redis = redis
        self.expire_time = expire_time

    def get_rewriter(self, url_rewriter, cookie_key):
        return DomainCacheCookieRewriter(url_rewriter, self, cookie_key)

    def get_cookie_headers(self, url, url_rewriter, cookie_key):
        subds = self.get_subdomains(url)
        host_cookie_rewriter = HostScopeNoFilterCookieRewriter(url_rewriter)

        if not subds:
            return None, None

        with redis.utils.pipeline(self.redis) as pi:
            for domain in subds:
                pi.hgetall(cookie_key + '.' + domain)

            all_res = pi.execute()

        cookies = []
        set_cookies = []

        expire_set = []

        for res, domain in zip(all_res, subds):
            if not res:
                continue

            for n, v in six.iteritems(res):
                if six.PY3 and type(n) == six.binary_type:
                    n = n.decode('utf-8')
                    v = v.decode('utf-8')

                full = n + '=' + v
                cookies.append(full.split(';')[0])

                full += '; Max-Age=' + str(self.expire_time)
                set_cookies.extend(host_cookie_rewriter.rewrite(full))

            expire_set.append(cookie_key + '.' + domain)

        with redis.utils.pipeline(self.redis) as pi:
            for key in expire_set:
                pi.expire(key, self.expire_time)

        cookies = ';'.join(cookies)
        return cookies, set_cookies

    def add_cookie(self, cookie_key, domain, name, value):
        if domain[0] != '.':
            domain = '.' + domain

        with redis.utils.pipeline(self.redis) as pi:
            pi.hset(cookie_key + domain, name, value)
            pi.expire(cookie_key + domain, self.expire_time)

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
class HostScopeNoFilterCookieRewriter(HostScopeCookieRewriter):
    def _filter_morsel(self, morsel):
        pass


# =============================================================================
class DomainCacheCookieRewriter(WbUrlBaseCookieRewriter):
    def __init__(self, url_rewriter, cookie_tracker, cookie_key):
        super(DomainCacheCookieRewriter, self).__init__(url_rewriter)
        self.cookie_tracker = cookie_tracker
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

            self.cookie_tracker.add_cookie(self.cookie_key,
                                           domain,
                                           morsel.key,
                                           string)

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

