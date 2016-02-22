import yaml
import re
import logging
import pkg_resources

from six.moves.urllib.parse import urlsplit

from pywb.utils.dsrules import BaseRule, RuleSet

from pywb.utils.canonicalize import unsurt, UrlCanonicalizer
from pywb.utils.loaders import to_native_str


#=================================================================
def load_domain_specific_cdx_rules(ds_rules_file, surt_ordered):
    canon = None
    fuzzy = None

    # Load Canonicalizer Rules
    rules = RuleSet(CDXDomainSpecificRule, 'canonicalize',
                    ds_rules_file=ds_rules_file)

    if not surt_ordered:
        for rule in rules.rules:
            rule.unsurt()

    if rules:
        canon = CustomUrlCanonicalizer(rules, surt_ordered)

    # Load Fuzzy Lookup Rules
    rules = RuleSet(CDXDomainSpecificRule, 'fuzzy_lookup',
                    ds_rules_file=ds_rules_file)

    if not surt_ordered:
        for rule in rules.rules:
            rule.unsurt()

    if rules:
        fuzzy = FuzzyQuery(rules)

    logging.debug('CustomCanonilizer? ' + str(bool(canon)))
    logging.debug('FuzzyMatcher? ' + str(bool(canon)))
    return (canon, fuzzy)


#=================================================================
class CustomUrlCanonicalizer(UrlCanonicalizer):
    def __init__(self, rules, surt_ordered=True):
        super(CustomUrlCanonicalizer, self).__init__(surt_ordered)
        self.rules = rules

    def __call__(self, url):
        urlkey = super(CustomUrlCanonicalizer, self).__call__(url)

        for rule in self.rules.iter_matching(urlkey):
            m = rule.regex.match(urlkey)
            if not m:
                continue

            if rule.replace:
                return m.expand(rule.replace)

        return urlkey


#=================================================================
class FuzzyQuery(object):
    def __init__(self, rules):
        self.rules = rules

    def __call__(self, query):
        matched_rule = None

        urlkey = to_native_str(query.key, 'utf-8')
        url = query.url
        filter_ = query.filters
        output = query.output

        for rule in self.rules.iter_matching(urlkey):
            m = rule.regex.search(urlkey)
            if not m:
                continue

            matched_rule = rule

            groups = m.groups()
            for g in groups:
                for f in matched_rule.filter:
                    filter_.append(f.format(g))

            break

        if not matched_rule:
            return None

        repl = '?'
        if matched_rule.replace:
            repl = matched_rule.replace

        inx = url.find(repl)
        if inx > 0:
            url = url[:inx + len(repl)]

        if matched_rule.match_type == 'domain':
            host = urlsplit(url).netloc
            # remove the subdomain
            url = host.split('.', 1)[1]

        params = query.params
        params.update({'url': url,
                       'matchType': matched_rule.match_type,
                       'filter': filter_})

        if 'reverse' in params:
            del params['reverse']

        if 'closest' in params:
            del params['closest']

        if 'end_key' in params:
            del params['end_key']

        return params


#=================================================================
class CDXDomainSpecificRule(BaseRule):
    DEFAULT_FILTER = ['~urlkey:{0}']
    DEFAULT_MATCH_TYPE = 'prefix'

    def __init__(self, name, config):
        super(CDXDomainSpecificRule, self).__init__(name, config)

        if not isinstance(config, dict):
            self.regex = self.make_regex(config)
            self.replace = None
            self.filter = self.DEFAULT_FILTER
            self.match_type = self.DEFAULT_MATCH_TYPE
        else:
            self.regex = self.make_regex(config.get('match'))
            self.replace = config.get('replace')
            self.filter = config.get('filter', self.DEFAULT_FILTER)
            self.match_type = config.get('type', self.DEFAULT_MATCH_TYPE)

    def unsurt(self):
        """
        urlkey is assumed to be in surt format by default
        In the case of non-surt format, this method is called
        to desurt any urls
        """
        self.url_prefix = list(map(unsurt, self.url_prefix))
        if self.regex:
            self.regex = re.compile(unsurt(self.regex.pattern))

        if self.replace:
            self.replace = unsurt(self.replace)

    @staticmethod
    def make_regex(config):
        # just query args
        if isinstance(config, list):
            string = CDXDomainSpecificRule.make_query_match_regex(config)

        # split out base and args
        elif isinstance(config, dict):
            string = config.get('regex', '')
            string += CDXDomainSpecificRule.make_query_match_regex(
                      config.get('args', []))

        # else assume string
        else:
            string = str(config)

        return re.compile(string)

    @staticmethod
    def make_query_match_regex(params_list):
        params_list.sort()

        def conv(value):
            return '[?&]({0}=[^&]+)'.format(re.escape(value))

        params_list = list(map(conv, params_list))
        final_str = '.*'.join(params_list)
        return final_str
