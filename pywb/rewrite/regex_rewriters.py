import re
from pywb.rewrite.content_rewriter import StreamingRewriter
from pywb.utils.loaders import load_py_name
from six.moves.urllib.parse import unquote


# =================================================================
class RxRules(object):
    HTTPX_MATCH_STR = r'https?:\\?/\\?/[A-Za-z0-9:_@.-]+'

    @staticmethod
    def remove_https(string, _):
        return string.replace("https", "http")

    @staticmethod
    def replace_str(replacer, match='this'):
        return lambda x, _: x.replace(match, replacer)

    @staticmethod
    def replace_prefix_from(prefix, match):
        def do_replace(x, _):
            start = x.find(match)
            if start == 0:
                return prefix
            if start > 0:
                return x[:start] + prefix
            return x

        return do_replace


    @staticmethod
    def format(template):
        return lambda string, _: template.format(string)

    @staticmethod
    def fixed(string):
        return lambda _, _2: string

    @staticmethod
    def archival_rewrite(mod=None):
        return lambda string, rewriter: rewriter.rewrite(string, mod)

    @staticmethod
    def add_prefix(prefix):
        return lambda string, _: prefix + string

    @staticmethod
    def add_suffix(suffix):
        return lambda string, _: string + suffix

    @staticmethod
    def compile_rules(rules):
        # Build regexstr, concatenating regex list
        regex_str = '|'.join(['(' + rx + ')' for rx, op, count in rules])

        # ensure it's not middle of a word, wrap in non-capture group
        regex_str = '(?:' + regex_str + ')'

        return re.compile(regex_str, re.M)

    def __init__(self, rules=None):
        self.rules = rules or []
        self.regex = self.compile_rules(self.rules)

    def __call__(self, extra_rules=None):
        if not extra_rules:
            return self.rules, self.regex

        all_rules = extra_rules + self.rules
        regex = self.compile_rules(all_rules)
        return all_rules, regex


# =================================================================
class JSWombatProxyRules(RxRules):
    def __init__(self):
        local_init_func = '\nvar {0} = function(name) {{\
return (self._wb_wombat && self._wb_wombat.local_init && \
self._wb_wombat.local_init(name)) || self[name]; }};\n\
if (!self.__WB_pmw) {{ self.__WB_pmw = function(obj) {{ this.__WB_source = obj; return this; }} }}\n\
{{\n'

        local_init_func_name = '_____WB$wombat$assign$function_____'

        local_init_func = local_init_func.format(local_init_func_name)

        local_var_line = 'let {0} = {1}("{0}");'

        # we must use a function to perform the this check because most minfiers reduce the number of statements
        # by turning everything into one or more expressions. Our previous rewrite was an logical expression,
        # (this && this._WB_wombat_obj_proxy || this), that would cause the outer expression to be invalid when
        # it was used as the LHS of certain expressions.
        # e.g. assignment expressions containing non parenthesized logical expression.
        # By using a function the expression injected is an call expression that plays nice in those cases
        this_rw = '_____WB$wombat$check$this$function_____(this)'

        check_loc = '((self.__WB_check_loc && self.__WB_check_loc(location, arguments)) || {}).href = '

        eval_str = 'WB_wombat_runEval2((_______eval_arg, isGlobal) => { var ge = eval; return isGlobal ? ge(_______eval_arg) : eval(_______eval_arg); }).eval(this, (function() { return arguments })(),'

        self.local_objs = [
            'window',
            'self',
            'document',
            'location',
            'top',
            'parent',
            'frames',
            'opener'
        ]

        local_declares = '\n'.join([local_var_line.format(obj, local_init_func_name) for obj in self.local_objs])
        local_declares += "\nlet arguments;"

        prop_str = '|'.join(self.local_objs)

        rules = [
            # rewriting 'eval(...)' - invocation
            (r'(?<!function)(?:\s|^)\beval\s*\(', self.replace_prefix_from(eval_str, 'eval'), 0),
            # rewriting 'x = eval' - no invocation
            (r'(?<=[=,])\s*\beval\b\s*(?![(:.$])', self.replace_str('self.eval', 'eval'), 0),
            (r'(?<=\.)postMessage\b\(', self.add_prefix('__WB_pmw(self).'), 0),
            (r'(?<![$.])\s*\blocation\b\s*[=]\s*(?![=])', self.add_suffix(check_loc), 0),
            # rewriting 'return this'
            (r'\breturn\s+this\b\s*(?![.$])', self.replace_str(this_rw), 0),
            # rewriting 'this.' special properties access
            (r'(?<![$.])\s*this\b(?=(?:\.(?:{0})\b))'.format(prop_str), self.replace_str(this_rw), 0),
            # rewrite '= this' or ', this'
            (r'(?<=[=,])\s*this\b\s*(?![:.$])', self.replace_str(this_rw), 0),
            # rewrite ')(this)'
            ('\}(?:\s*\))?\s*\(this\)', self.replace_str(this_rw), 0),
            # rewrite this in && or || expr?
            (r'(?<=[^|&][|&]{2})\s*this\b\s*(?![|&.$]([^|&]|$))', self.replace_str(this_rw), 0),
        ]

        super(JSWombatProxyRules, self).__init__(rules)

        self.first_buff = local_init_func + local_declares + '\n\n{'

        self.last_buff = '\n\n}}'


# =================================================================
class RegexRewriter(StreamingRewriter):
    rules_factory = RxRules()

    def __init__(self, rewriter, extra_rules=None, first_buff=''):
        super(RegexRewriter, self).__init__(rewriter, first_buff=first_buff)
        # rules = self.create_rules(http_prefix)
        self.rules, self.regex = self.rules_factory(extra_rules)

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

            result = op(m.group(i), self.url_rewriter)
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
                    replace = RxRules.archival_rewrite()
                elif 'function' in obj:
                    replace = load_py_name(obj['function'])
                else:
                    replace = RxRules.format(obj.get('replace', '{0}'))
                group = obj.get('group', 0)
                result = (match, replace, group)
                return result

            return list(map(parse_rule, config))

        return run_parse_rules


# =================================================================
class JSLocationRewriterRules(RxRules):
    """
    JS Rewriter mixin which rewrites location and domain to the
    specified prefix (default: ``WB_wombat_``)
    """

    def __init__(self, prefix='WB_wombat_'):
        super(JSLocationRewriterRules, self).__init__(self.get_rules(prefix))

    def get_rules(self, prefix):
        rules = [
            (r'(?<![$\'"])\b(?:location|top)\b(?![$\'":])', self.add_prefix(prefix), 0),

            (r'(?<=[?])\s*(?:\w+[.])?(location)\s*(?=[:])', self.add_prefix(prefix), 1),

            (r'(?<=\.)postMessage\b\(', self.add_prefix('__WB_pmw(self.window).'), 0),

            (r'(?<=\.)frameElement\b', self.add_prefix(prefix), 0),
        ]
        return rules


# =================================================================
class JSLinkAndLocationRewriterRules(JSLocationRewriterRules):
    """
    JS Rewriter rules which also rewrite absolute http://, https:// and // urls
    at the beginning of a string
    """
    # JS_HTTPX = r'(?:(?:(?<=["\';])https?:)|(?<=["\']))\\{0,4}/\\{0,4}/[A-Za-z0-9:_@.-]+.*(?=["\s\';&\\])'
    # JS_HTTPX = r'(?<=["\';])(?:https?:)?\\{0,4}/\\{0,4}/[A-Za-z0-9:_@.\-/\\?&#]+(?=["\';&\\])'

    # JS_HTTPX = r'(?:(?<=["\';])https?:|(?<=["\']))\\{0,4}/\\{0,4}/[A-Za-z0-9:_@.-][^"\s\';&\\]*(?=["\';&\\])'
    JS_HTTPX = r'(?:(?<=["\';])https?:|(?<=["\']))\\{0,4}/\\{0,4}/[A-Za-z0-9:_@%.\\-]+/'

    def get_rules(self, prefix):
        rules = super(JSLinkAndLocationRewriterRules, self).get_rules(prefix)
        rules.append((self.JS_HTTPX, RxRules.archival_rewrite(), 0))
        return rules


# =================================================================
class JSLocationOnlyRewriter(RegexRewriter):
    rules_factory = JSLocationRewriterRules()


# =================================================================
class JSLinkAndLocationRewriter(RegexRewriter):
    rules_factory = JSLinkAndLocationRewriterRules()


JSRewriter = JSLinkAndLocationRewriter

# =================================================================
class JSWombatProxyRewriter(RegexRewriter):
    """
    JS Rewriter mixin which wraps the contents of the
    script in an anonymous block scope and inserts
    Wombat js-proxy setup
    """

    rules_factory = JSWombatProxyRules()

    def __init__(self, rewriter, extra_rules=None):
        super(JSWombatProxyRewriter, self).__init__(rewriter, extra_rules=extra_rules)

        self.first_buff = self.rules_factory.first_buff
        self.last_buff = self.rules_factory.last_buff
        self.local_objs = self.rules_factory.local_objs

    def rewrite_complete(self, string, **kwargs):
        if not kwargs.get('inline_attr'):
            return super(JSWombatProxyRewriter, self).rewrite_complete(string)

        # check if any of the wrapped objects are used in the script
        # if not, don't rewrite
        if not any(obj in string for obj in self.local_objs):
            return string

        if string.startswith('javascript:'):
            string = 'javascript:' + self.first_buff + self.rewrite(string[len('javascript:'):])
        else:
            string = self.first_buff + self.rewrite(string)

        string += self.last_buff

        string = string.replace('\n', '')

        return string

    def final_read(self):
        return self.last_buff


# =================================================================
class JSNoneRewriter(RegexRewriter):
    pass


# =================================================================
class JSReplaceFuzzy(object):
    rx_obj = None

    def __init__(self, *args, **kwargs):
        super(JSReplaceFuzzy, self).__init__(*args, **kwargs)
        if not self.rx_obj:
            self.rx_obj = re.compile(self.rx)

    def rewrite(self, string):
        string = super(JSReplaceFuzzy, self).rewrite(string)
        cdx = self.url_rewriter.rewrite_opts['cdx']
        if cdx.get('is_fuzzy'):
            expected = unquote(cdx['url'])
            actual = unquote(self.url_rewriter.wburl.url)

            exp_m = self.rx_obj.search(expected)
            act_m = self.rx_obj.search(actual)

            if exp_m and act_m:
                result = string.replace(exp_m.group(1), act_m.group(1))
                if result != string:
                    string = result

        return string


# =================================================================
class CSSRules(RxRules):
    CSS_URL_REGEX = "url\\s*\\(\\s*(?:[\\\\\"']|(?:&.{1,4};))*\\s*([^)'\"]+)\\s*(?:[\\\\\"']|(?:&.{1,4};))*\\s*\\)"

    CSS_IMPORT_REGEX = ("@import\\s+(?:url\\s*)?\\(?\\s*['\"]?([\w.:/\\\\-]+)")

    def __init__(self):
        rules = [
            (self.CSS_URL_REGEX, self.archival_rewrite('oe_'), 1),
            (self.CSS_IMPORT_REGEX, self.archival_rewrite('cs_'), 1),
        ]

        super(CSSRules, self).__init__(rules)

# =================================================================
class CSSRewriter(RegexRewriter):
    rules_factory = CSSRules()


# =================================================================
class XMLRules(RxRules):
    def __init__(self):
        rules = [
            ('(?<![\w])([A-Za-z:]+[\s=]+)?["\'\s]*(' +
             self.HTTPX_MATCH_STR + ')',
             self.archival_rewrite(), 2),
        ]

        super(XMLRules, self).__init__(rules)


# =================================================================
class XMLRewriter(RegexRewriter):
    rules_factory = XMLRules()

    # custom filter to reject 'xmlns' attr
    def filter(self, m):
        attr = m.group(1)
        if attr and attr.startswith('xmlns'):
            return False

        return True



