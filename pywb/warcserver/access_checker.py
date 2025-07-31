from pywb.warcserver.index.indexsource import FileIndexSource
from pywb.warcserver.index.aggregator import DirectoryIndexSource, CacheDirectoryMixin
from pywb.warcserver.index.aggregator import SimpleAggregator
from pywb.warcserver.index.cdxobject import CDXObject

from pywb.utils.binsearch import search
from pywb.utils.merge import merge

from warcio.timeutils import timestamp_to_datetime
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
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
    # rules in the ACL file are followed by a white space (U+0020):
    # for searching we need a match suffix which sorts/compares after
    # (resp. before because we use the rev_cmp function). Simply add
    # another '#' (U+0023 > U+0020)
    EXACT_SUFFIX_SEARCH_B = b'####'  # type: bytes

    def __init__(self, access_source, default_access='allow', embargo=None):
        """Initialize a new AccessChecker

        :param str|list[str]|AccessRulesAggregator access_source: An access source
        :param str default_access: The default access action (allow)
        :param dict embargo: A dict specifying optional embargo setting
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

        self.embargo = self.parse_embargo(embargo)

    def parse_embargo(self, embargo):
        if not embargo:
            return None

        value = embargo.get('before')
        if value:
            embargo['before'] = timestamp_to_datetime(str(value), tz_aware=True)

        value = embargo.get('after')
        if value:
            embargo['after'] = timestamp_to_datetime(str(value), tz_aware=True)

        value = embargo.get('older')
        if value:
            delta = relativedelta(
                years=value.get('years', 0),
                months=value.get('months', 0),
                weeks=value.get('weeks', 0),
                days=value.get('days', 0))

            embargo['older'] = delta

        value = embargo.get('newer')
        if value:
            delta = relativedelta(
                years=value.get('years', 0),
                months=value.get('months', 0),
                weeks=value.get('weeks', 0),
                days=value.get('days', 0))

            embargo['newer'] = delta

        return embargo

    def check_embargo(self, url, ts):
        if not self.embargo:
            return None

        dt = timestamp_to_datetime(ts, tz_aware=True)
        access = self.embargo.get('access', 'exclude')

        # embargo before
        before = self.embargo.get('before')
        if before:
            print(dt, before)
            return access if dt < before else None

        # embargo after
        after = self.embargo.get('after')
        if after:
            return access if dt > after else None

        # embargo if newser than
        newer = self.embargo.get('newer')
        if newer:
            actual = datetime.now(timezone.utc) - newer
            return access if actual < dt else None

        # embargo if older than
        older = self.embargo.get('older')
        if older:
            actual = datetime.now(timezone.utc) - older
            return access if actual > dt else None

    def check_date_access(
        self, ts, access, default_access, rule
    ):
        """Return access based on date fields in access rule

        If a date-based rule exists and condition is not met, return default rule
        If no date-based rule exists, return access
        """
        if not rule:
            return access

        dt = timestamp_to_datetime(ts, tz_aware=True)

        before_ts = rule.get('before')
        if before_ts:
            before = timestamp_to_datetime(before_ts, tz_aware=True)
            return access if dt < before else default_access

        after_ts = rule.get('after')
        if after_ts:
            after = timestamp_to_datetime(after_ts, tz_aware=True)
            return access if dt > after else default_access

        newer = rule.get('newer')
        if newer:
            delta = relativedelta(
                years=newer.get('years', 0),
                months=newer.get('months', 0),
                weeks=newer.get('weeks', 0),
                days=newer.get('days', 0)
            )
            actual = datetime.now(timezone.utc) - delta
            return access if actual < dt else default_access

        older = rule.get('older')
        if older:
            delta = relativedelta(
                years=older.get('years', 0),
                months=older.get('months', 0),
                weeks=older.get('weeks', 0),
                days=older.get('days', 0)
            )
            actual = datetime.now(timezone.utc) - delta
            return access if actual > dt else default_access

        return access

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

    def find_access_rule(self, url, ts=None, urlkey=None, collection=None, acl_user=None):
        """Attempts to find the access control rule for the
        supplied URL otherwise returns the default rule

        :param str url: The URL for the rule to be found
        :param str|None ts: A timestamp (not used)
        :param str|None urlkey: The access control url key
        :param str|None collection: The collection, if any
        :param str|None acl_user: The access control user, if any
        :return: The access control rule for the supplied URL
        if one exists otherwise the default rule
        :rtype: CDXObject
        """
        params = {'url': url,
                  'urlkey': urlkey,
                  'nosource': 'true',
                  'exact_match_suffix': self.EXACT_SUFFIX_SEARCH_B
                 }
        if collection:
            params['param.coll'] = collection

        acl_iter, errs = self.aggregator(params)
        if errs:
            print(errs)

        key = params['key']
        key_exact = key + self.EXACT_SUFFIX_B

        tld = key.split(b',')[0]

        last_obj = None
        last_key = None

        for acl in acl_iter:

            # skip empty/invalid lines
            if not acl:
                continue

            acl_key = acl.split(b' ')[0]
            acl_obj = None

            if acl_key != last_key and last_obj:
                return last_obj

            if key_exact == acl_key:
                acl_obj = CDXObject(acl)

            if key.startswith(acl_key):
                acl_obj = CDXObject(acl)

            # Check for "*," in ACL, which matches any URL
            if acl_key == b"*,":
                acl_obj = CDXObject(acl)

            if acl_obj:
                user = acl_obj.get('user')
                if user == acl_user:
                    return acl_obj
                elif not user:
                    last_key = acl_key
                    last_obj = acl_obj

            # if acl key already less than first tld,
            # no match can be found
            if acl_key < tld:
                break

        return last_obj if last_obj else self.default_rule

    def __call__(self, res, acl_user):
        """Wraps the cdx iter in the supplied tuple returning a
        the wrapped cdx iter and the other members of the supplied
        tuple in same order

        :param tuple res: The result tuple
        :param str acl_user: The user associated with this request (optional)
        :return: An tuple
        """
        cdx_iter, errs = res
        return self.wrap_iter(cdx_iter, acl_user), errs

    def wrap_iter(self, cdx_iter, acl_user):
        """Wraps the supplied cdx iter and yields cdx objects
        that contain the access control results for the cdx object
        being yielded

        :param cdx_iter: The cdx object iterator to be wrapped
        :param str acl_user: The user associated with this request (optional)
        :return: The wrapped cdx object iterator
        """
        default_access = self.default_rule['access']

        for cdx in cdx_iter:
            url = cdx.get('url')
            timestamp = cdx.get('timestamp')

            # if no url, possible idx or other object, don't apply any checks and pass through
            if not url:
                yield cdx
                continue

            rule = None
            access = None

            if self.aggregator:
                rule = self.find_access_rule(
                    url,
                    timestamp,
                    cdx.get('urlkey'),
                    cdx.get('source-coll'),
                    acl_user
                )

                access = rule.get('access', 'exclude')

            access = self.check_date_access(
                timestamp, access, default_access, rule
            )

            if access != 'allow_ignore_embargo' and access != 'exclude':
                embargo_access = self.check_embargo(url, timestamp)
                if embargo_access and embargo_access != 'allow':
                    access = embargo_access

            if access == 'exclude':
                continue

            if not access:
                access = default_access

            if access == 'allow_ignore_embargo':
                access = 'allow'

            cdx['access'] = access
            yield cdx
