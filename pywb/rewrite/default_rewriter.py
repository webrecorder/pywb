from pywb.rewrite.content_rewriter import BaseContentRewriter

from pywb.rewrite.html_rewriter import HTMLRewriter
from pywb.rewrite.html_insert_rewriter import HTMLInsertOnlyRewriter

from pywb.rewrite.regex_rewriters import RegexRewriter, CSSRewriter, XMLRewriter
from pywb.rewrite.regex_rewriters import JSLocationOnlyRewriter, JSNoneRewriter, JSWombatProxyRewriter

from pywb.rewrite.header_rewriter import DefaultHeaderRewriter
from pywb.rewrite.cookie_rewriter import HostScopeCookieRewriter

from pywb.rewrite.jsonp_rewriter import JSONPRewriter

from pywb.rewrite.rewrite_dash import RewriteDASH
from pywb.rewrite.rewrite_hls import RewriteHLS
from pywb.rewrite.rewrite_amf import RewriteAMF

from pywb.rewrite.rewrite_js_workers import JSWorkerRewriter

from pywb import DEFAULT_RULES_FILE

import copy
from werkzeug.useragents import UserAgent


# ============================================================================
class DefaultRewriter(BaseContentRewriter):
    DEFAULT_REWRITERS = {
        'header': DefaultHeaderRewriter,
        'cookie': HostScopeCookieRewriter,

        'html': HTMLRewriter,
        'html-banner-only': HTMLInsertOnlyRewriter,

        'css': CSSRewriter,

        'js': JSLocationOnlyRewriter,
        'js-proxy': JSNoneRewriter,
        'js-worker': JSWorkerRewriter,

        'json': JSONPRewriter,

        'xml': XMLRewriter,

        'dash': RewriteDASH,

        'hls': RewriteHLS,

        'amf': RewriteAMF,
    }

    rewrite_types = {
        # HTML
        'text/html': 'guess-html',
        'application/xhtml': 'html',
        'application/xhtml+xml': 'html',

        # CSS
        'text/css': 'css',

        # JS
        'text/javascript': 'js',
        'application/javascript': 'js',
        'application/x-javascript': 'js',

        # JSON
        'application/json': 'json',

        # HLS
        'application/x-mpegURL': 'hls',
        'application/vnd.apple.mpegurl': 'hls',

        # DASH
        'application/dash+xml': 'dash',

        # AMF
        'application/x-amf': 'amf',

        # XML -- don't rewrite xml
        #'text/xml': 'xml',
        #'application/xml': 'xml',
        #'application/rss+xml': 'xml',

        # PLAIN
        'text/plain': 'guess-text',

        # DEFAULT or octet-stream
        '': 'guess-text',
        'application/octet-stream': 'guess-bin'
    }

    default_content_types = {
        'html': 'text/html',
        'css': 'text/css',
        'js': 'text/javascript'
    }

    def __init__(self, replay_mod='', config=None):
        config = config or {}
        rules_file = config.get('rules_file', DEFAULT_RULES_FILE)

        super(DefaultRewriter, self).__init__(rules_file, replay_mod)
        self.all_rewriters = copy.copy(self.DEFAULT_REWRITERS)

        self.add_prefer_mod('raw', 'id_')
        self.add_prefer_mod('banner-only', 'bn_')
        self.add_prefer_mod('rewritten', replay_mod)

    def init_js_regex(self, regexs):
        return RegexRewriter.parse_rules_from_config(regexs)

    def get_rewrite_types(self):
        return self.rewrite_types


# ============================================================================
class RewriterWithJSProxy(DefaultRewriter):
    def __init__(self, *args, **kwargs):
        super(RewriterWithJSProxy, self).__init__(*args, **kwargs)

    def get_rewriter(self, rw_type, rwinfo=None):
        if rw_type == 'js' and rwinfo:
            # check if UA allows this
            if self.ua_allows_obj_proxy(rwinfo.url_rewriter.rewrite_opts):
                return JSWombatProxyRewriter

        # otherwise, return default rewriter
        return super(RewriterWithJSProxy, self).get_rewriter(rw_type, rwinfo)

    def ua_allows_obj_proxy(self, opts):
        ua = opts.get('ua')
        if not ua:
            ua_string = opts.get('ua_string')
            if ua_string:
                ua = UserAgent(ua_string)

        if ua is None:
            return True

        supported = {
            'chrome': '49.0',
            'firefox': '44.0',
            'safari': '10.0',
            'opera': '36.0',
            'edge': '12.0',
            'msie': None,
        }

        min_vers = supported.get(ua.browser)

        return (min_vers and ua.version >= min_vers)
