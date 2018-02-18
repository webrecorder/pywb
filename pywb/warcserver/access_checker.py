from pywb.warcserver.index.indexsource import FileIndexSource
from pywb.warcserver.index.aggregator import DirectoryIndexSource, CacheDirectoryMixin

from pywb.utils.binsearch import search
from pywb.utils.merge import merge

import os


# ============================================================================
class FileAccessIndexSource(FileIndexSource):
    @staticmethod
    def rev_cmp(a, b):
        return (a < b) - (a > b)

    def _get_gen(self, fh, params):
        return search(fh, params['key'], prev_size=1, compare_func=self.rev_cmp)


# ============================================================================
class DirectoryAccessSource(DirectoryIndexSource):
    INDEX_SOURCES = [('.aclj', FileAccessIndexSource)]

    def _merge(self, iter_list):
        return merge(*(iter_list), reverse=True)


# ============================================================================
class CacheDirectoryAccessSource(CacheDirectoryMixin, DirectoryAccessSource):
    pass


# ============================================================================
class AccessChecker(object):
    def __init__(self, access_source_file, default_access='allow'):
        if isinstance(access_source_file, str):
            self.aggregator = self.create_access_aggregator(access_source_file)
        else:
            self.aggregator = access_source_file

        self.default_rule = {'urlkey': '', 'access': default_access}

    def create_access_aggregator(self, filename):
        if os.path.isdir(filename):
            return CacheDirectoryAccessSource(filename)

        elif os.path.isfile(filename):
            return FileAccessIndexSource(filename)

        else:
            raise Exception('Invalid Access Source: ' + filename)

    def find_access_rule(self, url, ts=None, urlkey=None):
        params = {'url': url, 'urlkey': urlkey}
        cdx_iter, errs = self.aggregator(params)
        if errs:
            print(errs)

        key = params['key'].decode('utf-8')

        for cdx in cdx_iter:
            if 'urlkey' not in cdx:
                continue

            if key.startswith(cdx['urlkey']):
                return cdx

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

            rule = self.find_access_rule(url, cdx.get('timestamp'), cdx.get('urlkey'))
            access = rule.get('access', 'exclude')
            if access == 'exclude':
                continue

            cdx['access'] = access
            yield cdx
