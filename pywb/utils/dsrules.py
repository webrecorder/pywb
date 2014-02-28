import yaml
import pkgutil

#=================================================================

DEFAULT_RULES_FILE = 'rules.yaml'
DEFAULT_RULES_PKG = 'pywb'


#=================================================================
class RuleSet(object):
    DEFAULT_KEY = ''

    def __init__(self, rule_cls, fieldname, **kwargs):
        """
        A domain specific rules block, inited via config map.
        If config map not specified, it is loaded from default location.

        The rules are represented as a map by domain.
        Each rules configuration will load is own field type
        from the list and given a specified rule_cls.
        """

        self.rules = []

        ds_rules_file = kwargs.get('ds_rules_file')
        default_rule_config = kwargs.get('default_rule_config')

        config = self.load_default_rules(ds_rules_file)

        rulesmap = config.get('rules') if config else None

        # if default_rule_config provided, always init a default ruleset
        if not rulesmap and default_rule_config is not None:
            self.rules = [rule_cls(self.DEFAULT_KEY, default_rule_config)]
            return

        def_key_found = False

        # iterate over master rules file
        for value in rulesmap:
            url_prefix = value.get('url_prefix')
            rules_def = value.get(fieldname)
            if not rules_def:
                continue

            if url_prefix == self.DEFAULT_KEY:
                def_key_found = True

            self.rules.append(rule_cls(url_prefix, rules_def))

        # if default_rule_config provided, always init a default ruleset
        if not def_key_found and default_rule_config is not None:
            self.rules.append(rule_cls(self.DEFAULT_KEY, default_rule_config))

    @staticmethod
    def load_default_rules(filename=None, pkg=None):
        config = None

        if not filename:
            filename = DEFAULT_RULES_FILE

        if not pkg:
            pkg = DEFAULT_RULES_PKG

        if filename:
            yaml_str = pkgutil.get_data(pkg, filename)
            config = yaml.load(yaml_str)

        return config

    def iter_matching(self, urlkey):
        """
        Iterate over all matching rules for given urlkey
        """
        for rule in self.rules:
            if rule.applies(urlkey):
                yield rule

    def get_first_match(self, urlkey):
        for rule in self.rules:
            if rule.applies(urlkey):
                return rule


#=================================================================
class BaseRule(object):
    """
    Base rule class -- subclassed to handle specific
    rules for given url_prefix key
    """
    def __init__(self, url_prefix, rules):
        self.url_prefix = url_prefix
        if not isinstance(self.url_prefix, list):
            self.url_prefix = [self.url_prefix]

    def applies(self, urlkey):
        return any(urlkey.startswith(x) for x in self.url_prefix)
