from warcio.utils import to_native_str

from pywb.utils.loaders import load_yaml_config
from pywb.utils.format import to_bool
from pywb import DEFAULT_RULES_FILE

import re
import os

from six import iterkeys
from six.moves.urllib.parse import urlsplit
from collections import namedtuple


# ============================================================================
FuzzyRule = namedtuple('FuzzyRule',
                       'url_prefix, regex, replace_after, filter_str, ' +
                       'match_type, find_all')


# ============================================================================
class FuzzyMatcher(object):
    DEFAULT_FILTER = ['urlkey:{0}']
    DEFAULT_MATCH_TYPE = 'prefix'
    DEFAULT_REPLACE_AFTER = '?'

    FUZZY_SKIP_PARAMS = ('alt_url', 'reverse', 'closest', 'end_key',
                         'url', 'matchType', 'filter')

    def __init__(self, filename=None):
        filename = filename or DEFAULT_RULES_FILE
        config = load_yaml_config(filename)
        self.rules = []
        for rule in config.get('rules'):
            rule = self.parse_fuzzy_rule(rule)
            if rule:
                self.rules.append(rule)

        self.default_filters = config.get('default_filters')

        self.fuzzy_search_limit = self.default_filters.get('fuzzy_search_limit')

        self.url_normalize_rx = [(re.compile(rule['match']), rule['replace']) for rule in self.default_filters['url_normalize']]

    def parse_fuzzy_rule(self, rule):
        """ Parse rules using all the different supported forms
        """
        url_prefix = rule.get('url_prefix')
        config = rule.get('fuzzy_lookup')
        if not config:
            return

        if not isinstance(url_prefix, list):
            url_prefix = [url_prefix]

        if not isinstance(config, dict):
            regex = self.make_regex(config)
            replace_after = self.DEFAULT_REPLACE_AFTER
            filter_str = self.DEFAULT_FILTER
            match_type = self.DEFAULT_MATCH_TYPE
            find_all = False

        else:
            regex = self.make_regex(config.get('match'))
            replace_after = config.get('replace', self.DEFAULT_REPLACE_AFTER)
            filter_str = config.get('filter', self.DEFAULT_FILTER)
            match_type = config.get('type', self.DEFAULT_MATCH_TYPE)
            find_all = config.get('find_all', False)

        return FuzzyRule(url_prefix, regex, replace_after, filter_str, match_type, find_all)

    def get_fuzzy_match(self, urlkey, url, params):
        filters = set()
        matched_rule = None

        for rule in self.rules:
            if not any((urlkey.startswith(prefix) for prefix in rule.url_prefix)):
                continue

            groups = None
            if rule.find_all:
                groups = rule.regex.findall(urlkey)
            else:
                m = rule.regex.search(urlkey)
                groups = m and m.groups()

            if groups is None:
                continue

            matched_rule = rule
            for g in groups:
                for f in matched_rule.filter_str:
                    filters.add(f.format(g))

            break

        if not matched_rule:
            return None

        # support matching w/o query if no additional filters
        # don't include trailing '?' if no filters and replace_after '?'
        no_filters = (not filters or filters == {'urlkey:'}) and (matched_rule.replace_after == '?')

        inx = url.find(matched_rule.replace_after)
        if inx > 0:
            length = inx + len(matched_rule.replace_after)
            # don't include trailing '?' for default filter
            if no_filters:
                length -= 1
                # don't include trailing '/' if match '/?'
                if url[length - 1] == '/':
                    length -= 1
            url = url[:length]
        elif not no_filters:
            url += matched_rule.replace_after[0]

        if matched_rule.match_type == 'domain':
            host = urlsplit(url).netloc
            url = host.split('.', 1)[1]

        fuzzy_params = {'url': url,
                        'matchType': matched_rule.match_type,
                        'filter': filters,
                        'is_fuzzy': '1'}

        if self.fuzzy_search_limit:
            fuzzy_params['limit'] = self.fuzzy_search_limit

        for key in iterkeys(params):
            if key not in self.FUZZY_SKIP_PARAMS:
                fuzzy_params[key] = params[key]

        return matched_rule, fuzzy_params

    def make_regex(self, config):
        if isinstance(config, list):
            string = self.make_query_match_regex(config)

        elif isinstance(config, dict):
            string = config.get('regex', '')
            string += self.make_query_match_regex(config.get('args', []))

        else:
            string = str(config)

        return re.compile(string)

    def make_query_match_regex(self, params_list):
        params_list.sort()

        def conv(value):
            return '[?&]({0}=[^&]+)'.format(re.escape(value))

        return '.*'.join([conv(param) for param in params_list])

    def __call__(self, index_source, params):
        cdx_iter, errs = index_source(params)
        return self.get_fuzzy_iter(cdx_iter, index_source, params), errs

    def get_fuzzy_iter(self, cdx_iter, index_source, params):
        found = False
        for cdx in cdx_iter:
            found = True
            yield cdx

        if found:
            return

        # if fuzzy matching disabled
        if not to_bool(params.get('allowFuzzy', True)):
            return

        url = params['url']
        urlkey = to_native_str(params['key'], 'utf-8')

        res = self.get_fuzzy_match(urlkey, url, params)
        if not res:
            return

        rule, fuzzy_params = res

        new_iter, errs = index_source(fuzzy_params)

        is_custom = (rule.url_prefix != [''])

        rx_cache = {}

        for cdx in new_iter:
            if is_custom or self.match_general_fuzzy_query(url, urlkey, cdx, rx_cache):
                cdx['is_fuzzy'] = '1'
                yield cdx

    def match_general_fuzzy_query(self, url, urlkey, cdx, rx_cache):
        check_query = False
        url_no_query, ext = self.get_ext(url)

        # don't fuzzy match to 204
        if cdx.get('status') == '204':
            if '__pywb_method=options' in cdx['urlkey']:
                return False

        # check ext
        if ext and ext not in self.default_filters['not_exts']:
            check_query = True

        else:
            # check mime
            mime = cdx.get('mime')
            if mime and mime in self.default_filters['mimes']:
                check_query = True

            # also check query if has method (non-GET request) or requestBody is set
            elif cdx.get('requestBody') or cdx.get('method'):
                check_query = True

        # if check_query, ensure matched url starts with original prefix, only differs by query
        if check_query:
            if cdx['url'] == url_no_query or cdx['url'].startswith(url_no_query + '?'):
                return True

        match_urlkey = cdx['urlkey']

        for normalize_rx in self.url_normalize_rx:
            match_urlkey = re.sub(normalize_rx[0], normalize_rx[1], match_urlkey)
            curr_urlkey = rx_cache.get(normalize_rx[0])

            if not curr_urlkey:
                curr_urlkey = re.sub(normalize_rx[0], normalize_rx[1], urlkey)
                rx_cache[normalize_rx[0]] = curr_urlkey
                urlkey = curr_urlkey

            if curr_urlkey == match_urlkey:
                return True

        return False

    def get_ext(self, url):
        # check last path segment
        # if contains '.', likely a file, so fuzzy match!
        url_no_query = url.split('?', 1)[0]
        last_path = url_no_query.rsplit('/', 1)[-1]
        return url_no_query, os.path.splitext(last_path)[1][1:]
