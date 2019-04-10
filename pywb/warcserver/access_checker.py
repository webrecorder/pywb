from pywb.warcserver.index.indexsource import FileIndexSource
from pywb.warcserver.index.aggregator import DirectoryIndexSource, CacheDirectoryMixin
from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.index.cdxobject import CDXObject

from pywb.utils.binsearch import search
from pywb.utils.merge import merge

import os


# ============================================================================
class FileAccessIndexSource(FileIndexSource):
    """An Index Source class specific to access control lists"""

    @staticmethod
    def rev_cmp(a, b):
        """Performs a comparison between two items using the
        algorithm of the removed builtin cmp

        :param a: A value to be compared
        :param b: A value to be compared
        :return: The result of the comparison
        :rtype: int
        """
        return (a < b) - (a > b)

    def _do_iter(self, fh, params):
        """Iterates over the supplied file handle to an access control list
        yielding the results of the search for the params key

        :param TextIO fh: The file handle to an access control list
        :param dict params: The params of the
        :return: A generator yielding the results of the param search
        """
        exact_suffix = params.get('exact_match_suffix')
        key = params['key']
        if exact_suffix:
            key += exact_suffix

        for line in search(fh, key, prev_size=1, compare_func=self.rev_cmp):
            yield line


# ============================================================================
class ReverseMergeMixin(object):
    """A mixin that provides revered merge functionality"""

    def _merge(self, iter_list):
        """Merges the supplied list of iterators in reverse

        :param iter_list: The list of iterators to be merged
        :return: An iterator that yields the results of the reverse merge
        """
        return merge(*(iter_list), reverse=True)


# ============================================================================
class AccessRulesAggregator(ReverseMergeMixin, SimpleAggregator):
    """An Aggregator specific to access control"""


# ============================================================================
class DirectoryAccessSource(ReverseMergeMixin, DirectoryIndexSource):
    """An directory index source specific to access control"""

    INDEX_SOURCES = [('.aclj', FileAccessIndexSource)]  # type: list[tuple]


# ============================================================================
class CacheDirectoryAccessSource(CacheDirectoryMixin, DirectoryAccessSource):
    """An cache directory index source specific to access control"""


# ============================================================================
class AccessChecker(object):
    """An access checker class"""

    EXACT_SUFFIX = '###'  # type: str
    EXACT_SUFFIX_B = b'###'  # type: bytes

    def __init__(self, access_source, default_access='allow'):
        """Initialize a new AccessChecker

        :param str|list[str]|AccessRulesAggregator access_source: An access source
        :param str default_access: The default access action (allow)
        """
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
        """Creates a new AccessRulesAggregator using the supplied list
        of access control file names

        :param list[str] source_files: The list of access control file names
        :return: The created AccessRulesAggregator
        :rtype: AccessRulesAggregator
        """
        sources = {}
        for filename in source_files:
            sources[filename] = self.create_access_source(filename)

        aggregator = AccessRulesAggregator(sources)
        return aggregator

    def create_access_source(self, filename):
        """Creates a new access source for the supplied filename.

        If the filename is for a directory an CacheDirectoryAccessSource
        instance is returned otherwise an FileAccessIndexSource instance

        :param str filename: The name of an file/directory
        :return: An instance of CacheDirectoryAccessSource or FileAccessIndexSource
        depending on if the supplied filename is for a directory or file
        :rtype: CacheDirectoryAccessSource|FileAccessIndexSource
        :raises Exception: Indicates an invalid access source was supplied
        """
        if os.path.isdir(filename):
            return CacheDirectoryAccessSource(filename)

        elif os.path.isfile(filename):
            return FileAccessIndexSource(filename)

        else:
            raise Exception('Invalid Access Source: ' + filename)

    def find_access_rule(self, url, ts=None, urlkey=None):
        """Attempts to find the access control rule for the
        supplied URL otherwise returns the default rule

        :param str url: The URL for the rule to be found
        :param str|None ts: A timestamp (not used)
        :param str|None urlkey: The access control url key
        :return: The access control rule for the supplied URL
        if one exists otherwise the default rule
        :rtype: CDXObject
        """
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
        """Wraps the cdx iter in the supplied tuple returning a
        the wrapped cdx iter and the other members of the supplied
        tuple in same order

        :param tuple res: The result tuple
        :return: An tuple
        """
        cdx_iter, errs = res
        return self.wrap_iter(cdx_iter), errs

    def wrap_iter(self, cdx_iter):
        """Wraps the supplied cdx iter and yields cdx objects
        that contain the access control results for the cdx object
        being yielded

        :param cdx_iter: The cdx object iterator to be wrapped
        :return: The wrapped cdx object iterator
        """
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
