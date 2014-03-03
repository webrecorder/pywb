from cdxobject import CDXObject, IDXObject, AccessException
from query import CDXQuery
from pywb.utils.timeutils import timestamp_to_sec

import bisect
import itertools
import re

from heapq import merge
from collections import deque


#=================================================================
def cdx_load(sources, query, perms_checker=None, process=True):
    """
    merge text CDX lines from sources, return an iterator for
    filtered and access-checked sequence of CDX objects.

    :param sources: iterable for text CDX sources.
    :param perms_checker: access check filter object implementing
      allow_url_lookup(key, url), allow_capture(cdxobj) and
      filter_fields(cdxobj) methods.
    :param process: bool, perform processing sorting/filtering/grouping ops
    """
    cdx_iter = load_cdx_streams(sources, query)
    cdx_iter = make_obj_iter(cdx_iter, query)

    if process and not query.secondary_index_only:
        cdx_iter = process_cdx(cdx_iter, query)

    if perms_checker:
        cdx_iter = restrict_cdx(cdx_iter, query, perms_checker)

    if query.output == 'text':
        cdx_iter = cdx_to_text(cdx_iter, query.fields)

    return cdx_iter


#=================================================================
def cdx_to_text(cdx_iter, fields):
    for cdx in cdx_iter:
        yield cdx.to_text(fields)


#=================================================================
def restrict_cdx(cdx_iter, query, perms_checker):
    """
    filter out those cdx records that user doesn't have access to,
    by consulting :param perms_checker:.
    :param cdx_iter: cdx record source iterable
    :param query: request parameters (CDXQuery)
    :param perms_checker: object implementing permission checker
    """
    if not perms_checker.allow_url_lookup(query.key, query.url):
        if query.is_exact:
            raise AccessException('Excluded')

    for cdx in cdx_iter:
        # TODO: we could let filter_fields handle this case by accepting
        # None as a return value.
        if not perms_checker.allow_capture(cdx):
            continue

        cdx = perms_checker.filter_fields(cdx)

        yield cdx


#=================================================================
def process_cdx(cdx_iter, query):
    if query.resolve_revisits:
        cdx_iter = cdx_resolve_revisits(cdx_iter)

    filters = query.filters
    if filters:
        cdx_iter = cdx_filter(cdx_iter, filters)

    collapse_time = query.collapse_time
    if collapse_time:
        cdx_iter = cdx_collapse_time_status(cdx_iter, collapse_time)

    limit = query.limit

    if query.reverse:
        cdx_iter = cdx_reverse(cdx_iter, limit)

    closest = query.closest
    if closest:
        cdx_iter = cdx_sort_closest(closest, cdx_iter, limit)

    if limit:
        cdx_iter = cdx_limit(cdx_iter, limit)

    return cdx_iter


#=================================================================
# load and source merge cdx streams
def load_cdx_streams(sources, query):
    # Optimize: no need to merge if just one input
    if len(sources) == 1:
        cdx_iter = sources[0].load_cdx(query)
    else:
        source_iters = map(lambda src: src.load_cdx(query), sources)
        cdx_iter = merge(*(source_iters))

    for cdx in cdx_iter:
        yield cdx


#=================================================================
# convert text cdx stream to CDXObject/IDXObject
def make_obj_iter(text_iter, query):
    # already converted
    if query.secondary_index_only:
        cls = IDXObject
    else:
        cls = CDXObject

    return (cls(line) for line in text_iter)


#=================================================================
# limit cdx to at most limit
def cdx_limit(cdx_iter, limit):
    for cdx, _ in itertools.izip(cdx_iter, xrange(limit)):
        yield cdx


#=================================================================
# reverse cdx
def cdx_reverse(cdx_iter, limit):
    # optimize for single last
    if limit == 1:
        last = None

        for cdx in cdx_iter:
            last = cdx

        return [last] if last else []

    reverse_cdxs = deque(maxlen=limit)

    for cdx in cdx_iter:
        reverse_cdxs.appendleft(cdx)

    return reverse_cdxs


 #=================================================================
# filter cdx by regex if each filter is field:regex form,
# apply filter to cdx[field]
def cdx_filter(cdx_iter, filter_strings):
    # Support single strings as well
    if isinstance(filter_strings, str):
        filter_strings = [filter_strings]

    filters = []

    class Filter:
        def __init__(self, string):
            # invert filter
            self.invert = string.startswith('!')
            if self.invert:
                string = string[1:]

            # exact match
            if string.startswith('='):
                string = string[1:]
                self.compare_func = self.exact
            # contains match
            elif string.startswith('~'):
                string = string[1:]
                self.compare_func = self.contains
            else:
                self.compare_func = self.regex

            parts = string.split(':', 1)
            # no field set, apply filter to entire cdx
            if len(parts) == 1:
                self.field = ''
            else:
            # apply filter to cdx[field]
                self.field = parts[0]
                string = parts[1]

            # make regex if regex mode
            if self.compare_func == self.regex:
                self.regex = re.compile(string)
            else:
                self.filter_str = string

        def __call__(self, cdx):
            val = cdx[self.field] if self.field else str(cdx)

            matched = self.compare_func(val)

            return matched ^ self.invert

        def exact(self, val):
            return (self.filter_str == val)

        def contains(self, val):
            return (self.filter_str in val)

        def regex(self, val):
            return self.regex.match(val) is not None

    filters = map(Filter, filter_strings)

    for cdx in cdx_iter:
        if all(x(cdx) for x in filters):
            yield cdx


#=================================================================
# collapse by timestamp and status code
def cdx_collapse_time_status(cdx_iter, timelen=10):
    timelen = int(timelen)

    last_token = None

    for cdx in cdx_iter:
        curr_token = (cdx['timestamp'][:timelen], cdx['statuscode'])

        # yield if last_dedup_time is diff, otherwise skip
        if curr_token != last_token:
            last_token = curr_token
            yield cdx


#=================================================================
# sort CDXCaptureResult by closest to timestamp
def cdx_sort_closest(closest, cdx_iter, limit=10):
    closest_cdx = []

    closest_sec = timestamp_to_sec(closest)

    for cdx in cdx_iter:
        sec = timestamp_to_sec(cdx['timestamp'])
        key = abs(closest_sec - sec)

        # create tuple to sort by key
        bisect.insort(closest_cdx, (key, cdx))

        if len(closest_cdx) == limit:
            # assuming cdx in ascending order and keys have started increasing
            if key > closest_cdx[-1]:
                break

        if len(closest_cdx) > limit:
            closest_cdx.pop()

    return itertools.imap(lambda x: x[1], closest_cdx)


#=================================================================
# resolve revisits

# Fields to append from cdx original to revisit
ORIG_TUPLE = ['length', 'offset', 'filename']


def cdx_resolve_revisits(cdx_iter):
    originals = {}

    for cdx in cdx_iter:
        is_revisit = cdx.is_revisit()

        digest = cdx['digest']

        original_cdx = originals.get(digest)

        if not original_cdx and not is_revisit:
            originals[digest] = cdx

        if original_cdx and is_revisit:
            fill_orig = lambda field: original_cdx[field]
            # Transfer mimetype and statuscode
            cdx['mimetype'] = original_cdx['mimetype']
            cdx['statuscode'] = original_cdx['statuscode']
        else:
            fill_orig = lambda field: '-'

        # Always add either the original or empty '- - -'
        for field in ORIG_TUPLE:
            cdx['orig.' + field] = fill_orig(field)

        yield cdx
