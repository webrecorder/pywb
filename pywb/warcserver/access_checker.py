from pywb.warcserver.index.indexsource import FileIndexSource
from pywb.warcserver.index.aggregator import DirectoryIndexSource, CacheDirectoryMixin
from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.index.cdxobject import CDXObject

from pywb.utils.binsearch import search
from pywb.utils.merge import merge

import os


# ============================================================================
class FileAccessIndexSource(FileIndexSource):
    @staticmethod
    def rev_cmp(a, b):
        return (a < b) - (a > b)

    def _do_iter(self, fh, params):
        exact_suffix = params.get('exact_match_suffix')
        key = params['key']
        if exact_suffix:
            key += exact_suffix

        for line in search(fh, key, prev_size=1, compare_func=self.rev_cmp):
            yield line


# ============================================================================
class ReverseMergeMixin(object):
    def _merge(self, iter_list):
        return merge(*(iter_list), reverse=True)


# ============================================================================
class AccessRulesAggregator(ReverseMergeMixin, SimpleAggregator):
    pass


# ============================================================================
class DirectoryAccessSource(ReverseMergeMixin, DirectoryIndexSource):
    INDEX_SOURCES = [('.aclj', FileAccessIndexSource)]


# ============================================================================
class CacheDirectoryAccessSource(CacheDirectoryMixin, DirectoryAccessSource):
    pass


# ============================================================================
class AccessChecker(object):
    EXACT_SUFFIX = '###'
    EXACT_SUFFIX_B = b'###'

    def __init__(self, access_source, default_access='allow'):
        if isinstance(access_source, str):
            self.aggregator = self.create_access_aggregator([access_source])
        elif isinstance(access_source, list):
            self.aggregator = self.create_access_aggregator(access_source)
        else:
            self.aggregator = access_source

        self.default_rule = CDXObject()
        self.default_rule['urlkey'] = ''
        self.default_rule['timestamp'] = '-'
        self.default_rule['access'] = default_access
        self.default_rule['default'] = 'true'

    def create_access_aggregator(self, source_files):
        sources = {}
        for filename in source_files:
            sources[filename] = self.create_access_source(filename)

        aggregator = AccessRulesAggregator(sources)
        return aggregator

    def create_access_source(self, filename):
        if os.path.isdir(filename):
            return CacheDirectoryAccessSource(filename)

        elif os.path.isfile(filename):
            return FileAccessIndexSource(filename)

        else:
            raise Exception('Invalid Access Source: ' + filename)

    def find_access_rule(self, url, ts=None, urlkey=None):
        params = {'url': url,
                  'urlkey': urlkey,
                  'nosource': 'true',
                  'exact_match_suffix': self.EXACT_SUFFIX_B
                 }

        acl_iter, errs = self.aggregator(params)
        if errs:
            print(errs)

        key = params['key']
        key_exact = key + self.EXACT_SUFFIX_B

        tld = key.split(b',')[0]

        for acl in acl_iter:

            # skip empty/invalid lines
            if not acl:
                continue

            acl_key = acl.split(b' ')[0]

            if key_exact == acl_key:
                return CDXObject(acl)

            if key.startswith(acl_key):
                return CDXObject(acl)

            # if acl key already less than first tld,
            # no match can be found
            if acl_key < tld:
                break

        return self.default_rule

    def __call__(self, res):
        cdx_iter, errs = res
        return self.wrap_iter(cdx_iter), errs

    def wrap_iter(self, cdx_iter):
        last_rule = None
        last_url = None

        for cdx in cdx_iter:
            url = cdx.get('url')
            # if no url, possible idx or other object, don't apply any checks and pass through
            if not url:
                yield cdx
                continue

            # TODO: optimization until date range support is included
            if url == last_url:
                rule = last_rule
            else:
                rule = self.find_access_rule(url, cdx.get('timestamp'), cdx.get('urlkey'))

            access = rule.get('access', 'exclude')
            if access == 'exclude':
                continue

            cdx['access'] = access
            yield cdx

            last_rule = rule
            last_url = url
