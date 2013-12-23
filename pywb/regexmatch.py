import re
import sys
from wburlrewriter import ArchivalUrlRewriter

class RegexMatchReplacer:
    def __init__(self, regexStr):
        self.regex = re.compile(regexStr)

    def replaceAll(self, string):
        last = 0
        result = ''
        for m in self.regex.finditer(string):
            start = m.start(1)
            end = m.end(1)
            result += string[last:start]
            result += self.replace(string[start:end], m)
            last = end

        result += string[last:]
        return result

    def replace(self, string, m):
        return string


class HttpMatchReplacer(RegexMatchReplacer):
    HTTP_REGEX = "(https?:\\\\?/\\\\?/[A-Za-z0-9:_@.-]+)"

    def __init__(self, rewriter):
        RegexMatchReplacer.__init__(self, HttpMatchReplacer.HTTP_REGEX)
        self.rewriter = rewriter

    def replace(self, string, m):
        return self.rewriter.rewrite(string)

class CustomMatchReplacer(RegexMatchReplacer):
    def __init__(self, matchRegex, replaceStr):
        RegexMatchReplacer.__init__(self, matchRegex)
        self.replaceStr = replaceStr

    def replace(self, string, m):
        return self.replaceStr

class Replacers:
    """
    >>> replacer.replaceAll('location = "http://example.com/abc.html"')
    'WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"'

    >>> replacer.replaceAll('cool_Location = "http://example.com/abc.html"')
    'cool_Location = "/web/20131010im_/http://example.com/abc.html"'

    >>> replacer.replaceAll('window.location = "http://example.com/abc.html"')
    'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"'
    """

    def __init__(self, replacers):
        self.replacers = replacers

    def replaceAll(self, string):
        for x in self.replacers:
            string = x.replaceAll(string)

        return string

replacer = Replacers([HttpMatchReplacer(ArchivalUrlRewriter('/20131010im_/http://abc.com/XYZ/', '/web/')), CustomMatchReplacer('[^\w]?(location|domain)', 'WB_wombat_location')])

# =================================
arw = ArchivalUrlRewriter('/20131010im_/http://abc.com/XYZ/', '/web/')



class MultiRegexReplacer:
    """
    >>> MultiRegexReplacer().replaceAll('location = "http://example.com/abc.html"', arw)
    'WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"'

    >>> MultiRegexReplacer().replaceAll('cool_Location = "http://example.com/abc.html"', arw)
    'cool_Location = "/web/20131010im_/http://example.com/abc.html"'

    >>> MultiRegexReplacer().replaceAll('window.location = "http://example.com/abc.html" document.domain = "anotherdomain.com"', arw)
    'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html" document.WB_wombat_domain = "anotherdomain.com"'

    """

    DEFAULT_RULES = [
     ('https?:\\\\?/\\\\?/[A-Za-z0-9:_@.-]+', ArchivalUrlRewriter.rewrite),
     ('location', 'WB_wombat_location'),
     ('domain', 'WB_wombat_domain'),
     ('some_func\(\)', '/* \\1 */')
     ]

    def __init__(self, rules = None):
        if not rules:
            rules = MultiRegexReplacer.DEFAULT_RULES

        # Build regexstr, concatenating regex list
        regexStr = '|'.join(['(' + rx + ')' for rx, op in rules])

        # ensure it's not middle of a word, wrap in non-capture group
        regexStr = '(?<!\w)(?:' + regexStr + ')'

        self.regex = re.compile(regexStr)
        self.rules = rules

    def replaceAll(self, string, rewriter):
        last = 0
        result = ''

        for m in self.regex.finditer(string):

            groups = m.groups()

            numGroups = len(groups)

            for g, i in zip(groups, range(numGroups)):
                if g:
                    break

            # Add 1 as group 0 is always entire match
            start = m.start(i + 1)
            end = m.end(i + 1)

            result += string[last:start]

            # i-th rule, 1st index of tuple
            op = self.rules[i][1]

            if hasattr(op, '__call__'):
                result += op(rewriter, string[start:end])
            else:
                result += str(op)

            last = end

        result += string[last:]
        return result



class RxRep:
    """
    >>> test_repl('location = "http://example.com/abc.html"')
    'WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"'

    >>> test_repl('cool_Location = "http://example.com/abc.html"')
    'cool_Location = "/web/20131010im_/http://example.com/abc.html"'

    >>> test_repl('window.location = "http://example.com/abc.html" document.domain = "anotherdomain.com"')
    'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html" document.WB_wombat_domain = "anotherdomain.com"'

    >>> test_repl('window.location = "http://example.com/abc.html"; some_func(); ')
    'window.WB_wombat_location = "/web/20131010im_/http://example.com/abc.html"; /*some_func()*/; '

    """

    @staticmethod
    def commentOut(string):
        return '/*' + string + '*/'

    @staticmethod
    def removeHttps(string):
        return string.replace("https", "http")

    @staticmethod
    def addPrefix(prefix):
        return lambda string: prefix + string

    HTTP_MATCH_REGEX = 'https?:\\\\?/\\\\?/[A-Za-z0-9:_@.-]+'

    DEFAULT_OP = addPrefix


    def __init__(self, rules):
        #rules = self.createRules(httpPrefix)

        # Build regexstr, concatenating regex list
        regexStr = '|'.join(['(' + rx + ')' for rx, op in rules])

        # ensure it's not middle of a word, wrap in non-capture group
        regexStr = '(?<!\w)(?:' + regexStr + ')'

        self.regex = re.compile(regexStr)
        self.rules = rules

    def replaceAll(self, string):
        return self.regex.sub(lambda x: self.replace(x), string)

    def replace(self, m):
        for group, (_, op) in zip(m.groups(), self.rules):
            if group:
                # Custom func
                if not hasattr(op, '__call__'):
                    op = RxRep.DEFAULT_OP(op)

                return op(group)

        raise re.error('No Match Found for replacement')


class JSRewriter(RxRep):
    def __init__(self, httpPrefix, extra = []):
        rules = self._createRules(httpPrefix)
        rules.extend(extra)
 
        RxRep.__init__(self, rules)


    def _createRules(self, httpPrefix):
        return [
             (RxRep.HTTP_MATCH_REGEX, httpPrefix),
             ('location', 'WB_wombat_'),
             ('domain', 'WB_wombat_'),
        ]



if __name__ == "__main__":
    import doctest

    extra = [('some_func\(\)', RxRep.commentOut)]

    rxrep = JSRewriter('/web/20131010im_/', extra)

    def test_repl(string):
        return rxrep.replaceAll(string)

    doctest.testmod()



