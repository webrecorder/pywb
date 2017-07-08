import re
from itertools import chain
from pywb.rewrite.content_rewriter import StreamingRewriter


# =================================================================
def load_function(string):
    import importlib

    string = string.split(':', 1)
    mod = importlib.import_module(string[0])
    return getattr(mod, string[1])


# =================================================================
class RegexRewriter(StreamingRewriter):
    # @staticmethod
    # def comment_out(string):
    #    return '/*' + string + '*/'

    @staticmethod
    def format(template):
        return lambda string: template.format(string)

    @staticmethod
    def remove_https(string):
        return string.replace("https", "http")

    @staticmethod
    def add_prefix(prefix):
        return lambda string: prefix + string

    @staticmethod
    def archival_rewrite(rewriter):
        return lambda string: rewriter.rewrite(string)

    # @staticmethod
    # def replacer(other):
    #    return lambda m, string: other

    HTTPX_MATCH_STR = r'https?:\\?/\\?/[A-Za-z0-9:_@.-]+'

    # DEFAULT_OP = add_prefix

    def __init__(self, rewriter, rules):
        super(RegexRewriter, self).__init__(rewriter)
        # rules = self.create_rules(http_prefix)

        # Build regexstr, concatenating regex list
        regex_str = '|'.join(['(' + rx + ')' for rx, op, count in rules])

        # ensure it's not middle of a word, wrap in non-capture group
        regex_str = '(?<!\w)(?:' + regex_str + ')'

        self.regex = re.compile(regex_str, re.M)
        self.rules = rules

    def filter(self, m):
        return True

    def rewrite(self, string):
        return self.regex.sub(lambda x: self.replace(x), string)

    def replace(self, m):
        i = 0
        for _, op, count in self.rules:
            i += 1

            full_m = i
            while count > 0:
                i += 1
                count -= 1

            if not m.group(i):
                continue

            # Optional filter to skip matches
            if not self.filter(m):
                return m.group(0)

            # Custom func
            # if not hasattr(op, '__call__'):
            #    op = RegexRewriter.DEFAULT_OP(op)

            result = op(m.group(i))
            final_str = result

            # if extracting partial match
            if i != full_m:
                final_str = m.string[m.start(full_m):m.start(i)]
                final_str += result
                final_str += m.string[m.end(i):m.end(full_m)]

            return final_str

    @staticmethod
    def parse_rules_from_config(config):
        def run_parse_rules(rewriter):
            def parse_rule(obj):
                match = obj.get('match')
                if 'rewrite' in obj:
                    replace = RegexRewriter.archival_rewrite(rewriter)
                elif 'function' in obj:
                    replace = load_function(obj['function'])
                else:
                    replace = RegexRewriter.format(obj.get('replace', '{0}'))
                group = obj.get('group', 0)
                result = (match, replace, group)
                return result

            return list(map(parse_rule, config))

        return run_parse_rules


# =================================================================
class JSLinkRewriterMixin(object):
    """
    JS Rewriter which rewrites absolute http://, https:// and // urls
    at the beginning of a string
    """
    # JS_HTTPX = r'(?:(?:(?<=["\';])https?:)|(?<=["\']))\\{0,4}/\\{0,4}/[A-Za-z0-9:_@.-]+.*(?=["\s\';&\\])'
    # JS_HTTPX = r'(?<=["\';])(?:https?:)?\\{0,4}/\\{0,4}/[A-Za-z0-9:_@.\-/\\?&#]+(?=["\';&\\])'

    # JS_HTTPX = r'(?:(?<=["\';])https?:|(?<=["\']))\\{0,4}/\\{0,4}/[A-Za-z0-9:_@.-][^"\s\';&\\]*(?=["\';&\\])'
    JS_HTTPX = r'(?:(?<=["\';])https?:|(?<=["\']))\\{0,4}/\\{0,4}/[A-Za-z0-9:_@%.\\-]+/'

    def __init__(self, rewriter, rules=[]):
        rules = rules + [
            (self.JS_HTTPX, RegexRewriter.archival_rewrite(rewriter), 0)
        ]
        super(JSLinkRewriterMixin, self).__init__(rewriter, rules)


# =================================================================
class JSLocationRewriterMixin(object):
    """
    JS Rewriter mixin which rewrites location and domain to the
    specified prefix (default: 'WB_wombat_')
    """

    def __init__(self, rewriter, rules=[], prefix='WB_wombat_'):
        rules = rules + [
            (r'(?<![$\'"])\b(?:location|top)\b(?![$\'":])', RegexRewriter.add_prefix(prefix), 0),

            (r'(?<=[?])\s*(?:\w+[.])?(location)\s*(?=[:])', RegexRewriter.add_prefix(prefix), 1),

            (r'(?<=\.)postMessage\b\(', RegexRewriter.add_prefix('__WB_pmw(self.window).'), 0),

            (r'(?<=\.)frameElement\b', RegexRewriter.add_prefix(prefix), 0),
        ]
        super(JSLocationRewriterMixin, self).__init__(rewriter, rules)


# =================================================================
class JSWombatProxyRewriterMixin(object):
    """
    JS Rewriter mixin which wraps the contents of the
    script in an anonymous block scope and inserts
    Wombat js-proxy setup
    """

    def __init__(self, rewriter, rules=[]):
        super(JSWombatProxyRewriterMixin, self).__init__(rewriter, rules)
        self.open_buffer = b"""
        var _____WB$wombat$assign$function_____=function(b){let c;switch(b){case'window':case'top':try{
        c=_WB_wombat_window_proxy}catch(d){c={}}break;case'self':try{c=_WB_wombat_window_proxy}catch(d){
        c=self}break;case'location':try{c=WB_wombat_location}catch(d){c={}}break;case'document':{let d=!0;try{
        c=_WB_wombat_document_proxy}catch(e){d=!1}if(!d)try{c=document}catch(e){c={}}break}}return c};\n
        {\n
            let window = _____WB$wombat$assign$function_____('window');\n
            let self = _____WB$wombat$assign$function_____('self');\n
            let document = _____WB$wombat$assign$function_____('document');\n
            let location = _____WB$wombat$assign$function_____('location');\n
            let top = _____WB$wombat$assign$function_____('top');\n\n
        """
        self.close_buffer = b"""\n\n}"""
        self.close_string = '\n\n}'

    def yield_fist_buffer(self):
        yield self.open_buffer

    def close_wrapper_buffer(self):
        return self.close_buffer

    def final_read_func(self):
        return self.close_string


# =================================================================
class JSLocationOnlyRewriter(JSLocationRewriterMixin, RegexRewriter):
    pass


# =================================================================
class JSLinkOnlyRewriter(JSLinkRewriterMixin, RegexRewriter):
    pass


# =================================================================
class JSLinkAndLocationRewriter(JSLocationRewriterMixin,
                                JSLinkRewriterMixin,
                                RegexRewriter):
    pass


# =================================================================
class JSNoneRewriter(RegexRewriter):
    def __init__(self, rewriter, rules=[]):
        super(JSNoneRewriter, self).__init__(rewriter, rules)


# =================================================================
class JSWombatProxyRewriter(JSWombatProxyRewriterMixin, RegexRewriter):
    def __init__(self, rewriter, rules=[]):
        super(JSWombatProxyRewriter, self).__init__(rewriter, rules)

    def rewrite_text_stream_to_gen(self, stream,
                                   rewrite_func,
                                   final_read_func,
                                   align_to_line):
        return chain(self.yield_fist_buffer(),
                     super(JSWombatProxyRewriter, self).rewrite_text_stream_to_gen(stream=stream,
                                                                                   rewrite_func=rewrite_func,
                                                                                   final_read_func=self.final_read_func,
                                                                                   align_to_line=align_to_line))


# =================================================================
# Set 'default' JSRewriter
JSRewriter = JSWombatProxyRewriter


# =================================================================
class XMLRewriter(RegexRewriter):
    def __init__(self, rewriter, extra=[]):
        rules = self._create_rules(rewriter)

        super(XMLRewriter, self).__init__(rewriter, rules)

    # custom filter to reject 'xmlns' attr
    def filter(self, m):
        attr = m.group(1)
        if attr and attr.startswith('xmlns'):
            return False

        return True

    def _create_rules(self, rewriter):
        return [
            ('([A-Za-z:]+[\s=]+)?["\'\s]*(' +
             RegexRewriter.HTTPX_MATCH_STR + ')',
             RegexRewriter.archival_rewrite(rewriter), 2),
        ]


# =================================================================
class CSSRewriter(RegexRewriter):
    CSS_URL_REGEX = "url\\s*\\(\\s*(?:[\\\\\"']|(?:&.{1,4};))*\\s*([^)'\"]+)\\s*(?:[\\\\\"']|(?:&.{1,4};))*\\s*\\)"

    CSS_IMPORT_NO_URL_REGEX = ("@import\\s+(?!url)\\(?\\s*['\"]?" +
                               "(?!url[\\s\\(])([\w.:/\\\\-]+)")

    def __init__(self, rewriter):
        rules = self._create_rules(rewriter)
        super(CSSRewriter, self).__init__(rewriter, rules)

    def _create_rules(self, rewriter):
        return [
            (CSSRewriter.CSS_URL_REGEX,
             RegexRewriter.archival_rewrite(rewriter), 1),

            (CSSRewriter.CSS_IMPORT_NO_URL_REGEX,
             RegexRewriter.archival_rewrite(rewriter), 1),
        ]
