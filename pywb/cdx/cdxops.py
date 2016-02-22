from pywb.cdx.cdxobject import CDXObject, IDXObject
from pywb.cdx.cdxobject import TIMESTAMP, STATUSCODE, MIMETYPE, DIGEST
from pywb.cdx.cdxobject import OFFSET, LENGTH, FILENAME

from pywb.cdx.query import CDXQuery
from pywb.utils.timeutils import timestamp_to_sec, pad_timestamp
from pywb.utils.timeutils import PAD_14_DOWN, PAD_14_UP

import bisect

from six.moves import zip, range, map
import re

from heapq import merge
from collections import deque


#=================================================================
def cdx_load(sources, query, process=True):
    """
    merge text CDX lines from sources, return an iterator for
    filtered and access-checked sequence of CDX objects.

    :param sources: iterable for text CDX sources.
    :param process: bool, perform processing sorting/filtering/grouping ops
    """
    cdx_iter = create_merged_cdx_gen(sources, query)

    # page count is a special case, no further processing
    if query.page_count:
        return cdx_iter

    cdx_iter = make_obj_iter(cdx_iter, query)

    if process and not query.secondary_index_only:
        cdx_iter = process_cdx(cdx_iter, query)

    custom_ops = query.custom_ops
    for op in custom_ops:
        cdx_iter = op(cdx_iter, query)

    if query.output == 'text':
        cdx_iter = cdx_to_text(cdx_iter, query.fields)
    elif query.output == 'json':
        cdx_iter = cdx_to_json(cdx_iter, query.fields)

    return cdx_iter


#=================================================================
def cdx_to_text(cdx_iter, fields):
    for cdx in cdx_iter:
        yield cdx.to_text(fields)


#=================================================================
def cdx_to_json(cdx_iter, fields):
    for cdx in cdx_iter:
        yield cdx.to_json(fields)


#=================================================================
def process_cdx(cdx_iter, query):
    if query.resolve_revisits:
        cdx_iter = cdx_resolve_revisits(cdx_iter)

    filters = query.filters
    if filters:
        cdx_iter = cdx_filter(cdx_iter, filters)

    if query.from_ts or query.to_ts:
        cdx_iter = cdx_clamp(cdx_iter, query.from_ts, query.to_ts)

    collapse_time = query.collapse_time
    if collapse_time:
        cdx_iter = cdx_collapse_time_status(cdx_iter, collapse_time)

    closest = query.closest
    reverse = query.reverse
    limit = query.limit

    if closest:
        cdx_iter = cdx_sort_closest(closest, cdx_iter, limit)

    elif reverse:
        cdx_iter = cdx_reverse(cdx_iter, limit)

    elif limit:
        cdx_iter = cdx_limit(cdx_iter, limit)

    return cdx_iter


#=================================================================
def create_merged_cdx_gen(sources, query):
    """
    create a generator which loads and merges cdx streams
    ensures cdxs are lazy loaded
    """
    # Optimize: no need to merge if just one input
    if len(sources) == 1:
        cdx_iter = sources[0].load_cdx(query)
    else:
        source_iters = map(lambda src: src.load_cdx(query), sources)
        cdx_iter = merge(*(source_iters))

    for cdx in cdx_iter:
        yield cdx


#=================================================================
def make_obj_iter(text_iter, query):
    """
    convert text cdx stream to CDXObject/IDXObject.
    """
    if query.secondary_index_only:
        cls = IDXObject
    else:
        cls = CDXObject

    return (cls(line) for line in text_iter)


#=================================================================
def cdx_limit(cdx_iter, limit):
    """
    limit cdx to at most `limit`.
    """
#    for cdx, _ in itertools.izip(cdx_iter, xrange(limit)):
#        yield cdx
    return (cdx for cdx, _ in zip(cdx_iter, range(limit)))


#=================================================================
def cdx_reverse(cdx_iter, limit):
    """
    return cdx records in reverse order.
    """
    # optimize for single last
    if limit == 1:
        last = None

        for cdx in cdx_iter:
            last = cdx

        if not last:
            return
        yield last

    reverse_cdxs = deque(maxlen=limit)

    for cdx in cdx_iter:
        reverse_cdxs.appendleft(cdx)

    for cdx in reverse_cdxs:
        yield cdx


#=================================================================
def cdx_filter(cdx_iter, filter_strings):
    """
    filter CDX by regex if each filter is :samp:`{field}:{regex}` form,
    apply filter to :samp:`cdx[{field}]`.
    """
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
            # apply filter to cdx[field]
            else:
                self.field = parts[0]
                self.field = CDXObject.CDX_ALT_FIELDS.get(self.field,
                                                          self.field)
                string = parts[1]

            # make regex if regex mode
            if self.compare_func == self.regex:
                self.regex = re.compile(string)
            else:
                self.filter_str = string

        def __call__(self, cdx):
            if not self.field:
                val = str(cdx)
            else:
                val = cdx.get(self.field, '')

            matched = self.compare_func(val)

            return matched ^ self.invert

        def exact(self, val):
            return (self.filter_str == val)

        def contains(self, val):
            return (self.filter_str in val)

        def regex(self, val):
            return self.regex.match(val) is not None

    filters = list(map(Filter, filter_strings))

    for cdx in cdx_iter:
        if all(x(cdx) for x in filters):
            yield cdx


#=================================================================
def cdx_clamp(cdx_iter, from_ts, to_ts):
    """
    Clamp by start and end ts
    """
    if from_ts and len(from_ts) < 14:
        from_ts = pad_timestamp(from_ts, PAD_14_DOWN)

    if to_ts and len(to_ts) < 14:
        to_ts = pad_timestamp(to_ts, PAD_14_UP)

    for cdx in cdx_iter:
        if from_ts and cdx[TIMESTAMP] < from_ts:
            continue

        if to_ts and cdx[TIMESTAMP] > to_ts:
            continue

        yield cdx


#=================================================================
def cdx_collapse_time_status(cdx_iter, timelen=10):
    """
    collapse by timestamp and status code.
    """
    timelen = int(timelen)

    last_token = None

    for cdx in cdx_iter:
        curr_token = (cdx[TIMESTAMP][:timelen], cdx.get(STATUSCODE, ''))

        # yield if last_dedup_time is diff, otherwise skip
        if curr_token != last_token:
            last_token = curr_token
            yield cdx


#=================================================================
def cdx_sort_closest(closest, cdx_iter, limit=10):
    """
    sort CDXCaptureResult by closest to timestamp.
    """
    closest_cdx = []
    closest_keys = []
    closest_sec = timestamp_to_sec(closest)

    for cdx in cdx_iter:
        sec = timestamp_to_sec(cdx[TIMESTAMP])
        key = abs(closest_sec - sec)

        # create tuple to sort by key
        #bisect.insort(closest_cdx, (key, cdx))

        i = bisect.bisect_right(closest_keys, key)
        closest_keys.insert(i, key)
        closest_cdx.insert(i, cdx)

        if len(closest_cdx) == limit:
            # assuming cdx in ascending order and keys have started increasing
            if key > closest_keys[-1]:
                break

        if len(closest_cdx) > limit:
            closest_cdx.pop()

    for cdx in closest_cdx:
        yield cdx

    #for cdx in map(lambda x: x[1], closest_cdx):
    #    yield cdx


#=================================================================
# resolve revisits

# Fields to append from cdx original to revisit
ORIG_TUPLE = [LENGTH, OFFSET, FILENAME]


def cdx_resolve_revisits(cdx_iter):
    """
    resolve revisits.

    this filter adds three fields to CDX: ``orig.length``, ``orig.offset``,
    and ``orig.filename``. for revisit records, these fields have corresponding
    field values in previous non-revisit (original) CDX record.
    They are all ``"-"`` for non-revisit records.
    """
    originals = {}

    for cdx in cdx_iter:
        is_revisit = cdx.is_revisit()

        digest = cdx.get(DIGEST)

        original_cdx = None

        # only set if digest is valid, otherwise no way to resolve
        if digest:
            original_cdx = originals.get(digest)

            if not original_cdx and not is_revisit:
                originals[digest] = cdx

        if original_cdx and is_revisit:
            fill_orig = lambda field: original_cdx.get(field, '-')
            # Transfer mimetype and statuscode
            if MIMETYPE in cdx:
                cdx[MIMETYPE] = original_cdx.get(MIMETYPE, '')
            if STATUSCODE in cdx:
                cdx[STATUSCODE] = original_cdx.get(STATUSCODE, '')
        else:
            fill_orig = lambda field: '-'

        # Always add either the original or empty '- - -'
        for field in ORIG_TUPLE:
            cdx['orig.' + field] = fill_orig(field)

        yield cdx
