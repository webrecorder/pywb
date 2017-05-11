from pywb.rewrite.content_rewriter import BaseContentRewriter

from pywb.rewrite.html_rewriter import HTMLRewriter

from pywb.rewrite.regex_rewriters import RegexRewriter, CSSRewriter, XMLRewriter
from pywb.rewrite.regex_rewriters import JSLinkAndLocationRewriter, JSLinkOnlyRewriter
from pywb.rewrite.regex_rewriters import JSLocationOnlyRewriter, JSNoneRewriter

from pywb.urlrewrite.header_rewriter import PrefixHeaderRewriter, ProxyHeaderRewriter

from pywb.rewrite.jsonp_rewriter import JSONPRewriter

from pywb.rewrite.rewrite_dash import RewriteDASH
from pywb.rewrite.rewrite_hls import RewriteHLS
from pywb.rewrite.rewrite_amf import RewriteAMF


# ============================================================================
class DefaultRewriter(BaseContentRewriter):
    all_rewriters = {
        'header': PrefixHeaderRewriter,
        'header-proxy': ProxyHeaderRewriter,

        'html': HTMLRewriter,

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

        # XML
        'text/xml': 'xml',
        'application/xml': 'xml',
        'application/rss+xml': 'xml',

        # PLAIN
        'text/plain': 'plain',
    }

    def init_js_regex(self, regexs):
        return RegexRewriter.parse_rules_from_config(regexs)

    def get_rewrite_types(self):
        return self.rewrite_types
