import yaml
import re
import logging
import pkgutil

from pywb.utils.dsrules import BaseRule, RuleSet

from canonicalize import unsurt, UrlCanonicalizer


#=================================================================
def load_domain_specific_cdx_rules(filename, surt_ordered):
    #fh = pkgutil.get_data(__package__, filename)
    #config = yaml.load(fh)

    canon = None
    fuzzy = None

    # Load Canonicalizer Rules
    rules = RuleSet(CDXDomainSpecificRule, 'canonicalize')

    if not surt_ordered:
        for rule in rules:
            rule.unsurt()

    if rules:
        canon = CustomUrlCanonicalizer(rules, surt_ordered)

    # Load Fuzzy Lookup Rules
    rules = RuleSet(CDXDomainSpecificRule, 'fuzzy_lookup')

    if not surt_ordered:
        for rule in rules:
            rule.unsurt()

    if rules:
        fuzzy = FuzzyQuery(rules)

    logging.debug('CANON: ' + str(canon))
    logging.debug('FUZZY: ' + str(fuzzy))
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
class FuzzyQuery:
    def __init__(self, rules):
        self.rules = rules

    def __call__(self, params):
        matched_rule = None

        urlkey = params['key']
        url = params['url']

        for rule in self.rules.iter_matching(urlkey):
            m = rule.regex.search(urlkey)
            if not m:
                continue

            matched_rule = rule

            if len(m.groups()) == 1:
                params['filter'] = '=urlkey:' + m.group(1)

            break

        if not matched_rule:
            return None

        inx = url.find('?')
        if inx > 0:
            params['url'] = url[:inx + 1]

        params['matchType'] = 'prefix'
        params['key'] = None
        return params


#=================================================================
class CDXDomainSpecificRule(BaseRule):
    def __init__(self, name, config):
        super(CDXDomainSpecificRule, self).__init__(name, config)

        if isinstance(config, basestring):
            self.regex = re.compile(config)
            self.replace = None
        else:
            self.regex = re.compile(config.get('match'))
            self.replace = config.get('replace')

    def unsurt(self):
        """
        urlkey is assumed to be in surt format by default
        In the case of non-surt format, this method is called
        to desurt any urls
        """
        self.url_prefix = map(unsurt, self.url_prefix)
        if self.regex:
            self.regex = unsurt(self.regex)

        if self.replace:
            self.replace = unsurt(self.replace)

    @staticmethod
    def load_rules(rules_config, surt_ordered=True):
        if not rules_config:
            return []

        rules = map(StartsWithRule, rules_config)

        if not surt_ordered:
            for rule in rules:
                rule.unsurt()

        return rules
