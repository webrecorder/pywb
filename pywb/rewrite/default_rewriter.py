import copy

from werkzeug.useragents import UserAgent

from pywb import DEFAULT_RULES_FILE
from pywb.rewrite.content_rewriter import BaseContentRewriter
from pywb.rewrite.cookie_rewriter import HostScopeCookieRewriter
from pywb.rewrite.header_rewriter import DefaultHeaderRewriter
from pywb.rewrite.html_insert_rewriter import HTMLInsertOnlyRewriter
from pywb.rewrite.html_rewriter import HTMLRewriter
from pywb.rewrite.jsonp_rewriter import JSONPRewriter
from pywb.rewrite.regex_rewriters import (
    CSSRewriter,
    JSLocationOnlyRewriter,
    JSNoneRewriter,
    JSWombatProxyRewriter,
    RegexRewriter,
    XMLRewriter,
)
from pywb.rewrite.rewrite_amf import RewriteAMF
from pywb.rewrite.rewrite_dash import RewriteDASH
from pywb.rewrite.rewrite_hls import RewriteHLS
from pywb.utils.constants import ContentRewriteTypes


# ============================================================================
class DefaultRewriter(BaseContentRewriter):
    DEFAULT_REWRITERS = {
        ContentRewriteTypes.header: DefaultHeaderRewriter,
        ContentRewriteTypes.cookie: HostScopeCookieRewriter,
        ContentRewriteTypes.html: HTMLRewriter,
        ContentRewriteTypes.html_banner_only: HTMLInsertOnlyRewriter,
        ContentRewriteTypes.css: CSSRewriter,
        ContentRewriteTypes.js: JSLocationOnlyRewriter,
        ContentRewriteTypes.js_proxy: JSNoneRewriter,
        ContentRewriteTypes.json: JSONPRewriter,
        ContentRewriteTypes.xml: XMLRewriter,
        ContentRewriteTypes.dash: RewriteDASH,
        ContentRewriteTypes.hls: RewriteHLS,
        ContentRewriteTypes.amf: RewriteAMF,
    }

    rewrite_types = {
        # HTML
        'text/html': ContentRewriteTypes.guess_html,
        'application/xhtml': ContentRewriteTypes.html,
        'application/xhtml+xml': ContentRewriteTypes.html,
        # CSS
        'text/css': ContentRewriteTypes.css,
        # JS
        'text/javascript': ContentRewriteTypes.js,
        'application/javascript': ContentRewriteTypes.js,
        'application/x-javascript': ContentRewriteTypes.js,
        # JSON
        'application/json': ContentRewriteTypes.json,
        # HLS
        'application/x-mpegURL': ContentRewriteTypes.hls,
        'application/vnd.apple.mpegurl': ContentRewriteTypes.hls,
        # DASH
        'application/dash+xml': ContentRewriteTypes.dash,
        # AMF
        'application/x-amf': ContentRewriteTypes.amf,
        # XML -- don't rewrite xml
        # 'text/xml': 'xml',
        # 'application/xml': 'xml',
        # 'application/rss+xml': 'xml',
        # PLAIN
        'text/plain': ContentRewriteTypes.guess_text,
        # DEFAULT or octet-stream
        '': ContentRewriteTypes.guess_text,
        'application/octet-stream': ContentRewriteTypes.guess_bin,
    }

    default_content_types = {
        ContentRewriteTypes.html: 'text/html',
        ContentRewriteTypes.css: 'text/css',
        ContentRewriteTypes.js: 'text/javascript',
    }

    def __init__(self, replay_mod='', config=None):
        config = config or {}
        rules_file = config.get('rules_file', DEFAULT_RULES_FILE)
        super(DefaultRewriter, self).__init__(rules_file, replay_mod)
        self.all_rewriters = copy.copy(self.DEFAULT_REWRITERS)

    def init_js_regex(self, regexs):
        return RegexRewriter.parse_rules_from_config(regexs)

    def get_rewrite_types(self):
        return self.rewrite_types


# ============================================================================
class RewriterWithJSProxy(DefaultRewriter):
    OBJECT_PROXY_SUPPORTED_UA = {
        'chrome': '49.0',
        'firefox': '44.0',
        'safari': '10.0',
        'opera': '36.0',
        'edge': '12.0',
        'msie': None,
    }

    def __init__(self, *args, **kwargs):
        super(RewriterWithJSProxy, self).__init__(*args, **kwargs)

    def get_rewriter(self, rw_type, rwinfo=None):
        if rw_type == ContentRewriteTypes.js and rwinfo:
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

        min_vers = self.OBJECT_PROXY_SUPPORTED_UA.get(ua.browser)

        return min_vers and ua.version >= min_vers
