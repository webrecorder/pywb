from pywb.rewrite.content_rewriter import BaseContentRewriter

from pywb.rewrite.html_rewriter import HTMLRewriter
from pywb.rewrite.html_insert_rewriter import HTMLInsertOnlyRewriter

from pywb.rewrite.regex_rewriters import RegexRewriter, CSSRewriter, XMLRewriter
from pywb.rewrite.regex_rewriters import JSLocationOnlyRewriter, JSNoneRewriter, JSWombatProxyRewriter

from pywb.rewrite.header_rewriter import PrefixHeaderRewriter
from pywb.rewrite.cookie_rewriter import HostScopeCookieRewriter

from pywb.rewrite.jsonp_rewriter import JSONPRewriter

from pywb.rewrite.rewrite_dash import RewriteDASH
from pywb.rewrite.rewrite_hls import RewriteHLS
from pywb.rewrite.rewrite_amf import RewriteAMF

import copy


# ============================================================================
class DefaultRewriter(BaseContentRewriter):
    DEFAULT_REWRITERS = {
        'header': PrefixHeaderRewriter,
        'cookie': HostScopeCookieRewriter,

        'html': HTMLRewriter,
        'html-banner-only': HTMLInsertOnlyRewriter,

        'css': CSSRewriter,

        'js': JSLocationOnlyRewriter,
        'js-proxy': JSNoneRewriter,

        'json': JSONPRewriter,

        'xml': XMLRewriter,

        'dash': RewriteDASH,

        'hls': RewriteHLS,

        'amf': RewriteAMF,
    }

    rewrite_types = {
        # HTML
        'text/html': 'html',
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

        # DASH
        'application/dash+xml': 'dash',

        # AMF
        'application/x-amf': 'amf',

        # XML -- don't rewrite xml
        #'text/xml': 'xml',
        #'application/xml': 'xml',
        #'application/rss+xml': 'xml',

        # PLAIN
        'text/plain': 'plain',
    }

    def __init__(self, rules_file=None, replay_mod=''):
        rules_file = rules_file or 'pkg://pywb/rules.yaml'
        self.all_rewriters = copy.copy(self.DEFAULT_REWRITERS)
        super(DefaultRewriter, self).__init__(rules_file, replay_mod)

    def init_js_regex(self, regexs):
        return RegexRewriter.parse_rules_from_config(regexs)

    def get_rewrite_types(self):
        return self.rewrite_types


# ============================================================================
class DefaultRewriterWithJSProxy(DefaultRewriter):
    def __init__(self, *args, **kwargs):
        super(DefaultRewriterWithJSProxy, self).__init__(*args, **kwargs)
        self.all_rewriters['js'] = JSWombatProxyRewriter

