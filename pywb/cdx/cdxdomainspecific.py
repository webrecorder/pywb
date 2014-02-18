import yaml
import re
import logging
import pkgutil

from canonicalize import unsurt, UrlCanonicalizer


#=================================================================
def load_domain_specific_cdx_rules(filename, surt_ordered):
    fh = pkgutil.get_data(__package__, filename)
    config = yaml.load(fh)

    # Load Canonicalizer Rules
    rules = StartsWithRule.load_rules(config.get('canon_rules'),
                                      surt_ordered)

    if rules:
        canon = CustomUrlCanonicalizer(rules, surt_ordered)
    else:
        canon = None

    # Load Fuzzy Lookup Rules
    rules = StartsWithRule.load_rules(config.get('fuzzy_lookup_rules'),
                                      surt_ordered)

    if rules:
        fuzzy = FuzzyQuery(rules)
    else:
        fuzzy = None

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

        for rule in self.rules:
            if not any(urlkey.startswith(x) for x in rule.starts):
                continue

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

        for rule in self.rules:
            if not any(urlkey.startswith(x) for x in rule.starts):
                continue

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
class StartsWithRule:
    def __init__(self, config, surt_ordered=True):
        self.starts = config.get('startswith')
        if not isinstance(self.starts, list):
            self.starts = [self.starts]

        self.regex = re.compile(config.get('matches'))
        self.replace = config.get('replace')

    def unsurt(self):
        # must convert to non-surt form
        self.starts = map(unsurt, self.starts)
        self.regex = unsurt(self.regex)
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
