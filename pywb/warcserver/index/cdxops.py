from pywb.warcserver.index.cdxobject import CDXObject, IDXObject, URLKEY
from pywb.warcserver.index.cdxobject import TIMESTAMP, STATUSCODE, MIMETYPE, DIGEST
from pywb.warcserver.index.cdxobject import OFFSET, LENGTH, FILENAME

from pywb.warcserver.index.query import CDXQuery
from pywb.utils.format import to_bool

from warcio.timeutils import timestamp_to_sec, sec_to_timestamp, pad_timestamp
from warcio.timeutils import PAD_14_DOWN, PAD_14_UP

import logging

from six.moves import zip, range, map
import re

from heapq import merge, heappush, heapreplace
from collections import deque


logger = logging.getLogger('warcserver')

# a closest lookup that reads at least this many captures logs a warning.
# Usually a url with a very large number of captures, eg. a script embedded
# in many pages, which makes each replay of these pages slow
CLOSEST_WARN_CAPTURES = 50000


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
        # an exact query yields the captures of a single url, merged from the
        # sources in ascending timestamp order
        cdx_iter = cdx_sort_closest(closest, cdx_iter, limit,
                                    sorted_input=query.is_exact)

    elif reverse:
        cdx_iter = cdx_reverse(cdx_iter, limit)

    elif limit:
        cdx_iter = cdx_limit(cdx_iter, limit)

    return cdx_iter


#=================================================================
def closest_seek_limit(params):
    """
    Return the limit if process_cdx() would only keep the 'limit' captures
    closest to 'closest' of a single url, and nothing before the sort removes
    or changes captures. An index source can then read only the captures
    around 'closest' instead of every capture of the url.
    Otherwise, return None.
    """
    if not params.get('closest'):
        return None

    # exact match: a single urlkey
    if params.get('matchType') != 'exact' or params.get('end_key') != params.get('key', b'') + b'!':
        return None

    # (paged index queries are not processed at all)
    for name in ('resolveRevisits', 'reverse', 'showNumPages', 'showPagedIndex'):
        if to_bool(params.get(name)):
            return None

    if params.get('sort') == 'reverse':
        return None

    for name in ('filter', 'from', 'from_ts', 'to', 'collapseTime'):
        if params.get(name):
            return None

    try:
        # the same limit as CDXQuery.limit: replay lookups have no explicit
        # limit, but a _closest_limit set by the ResourceHandler
        if 'limit' in params:
            limit = int(params['limit'])
        else:
            limit = int(params.get('_closest_limit') or 100000)
    except ValueError:
        return None

    return limit if limit > 0 else None


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
class CDXFilter(object):
    def __init__(self, string):
        # invert filter
        self.invert = string.startswith('!')
        if self.invert:
            string = string[1:]

        # exact match
        if string.startswith('='):
            string = string[1:]
            self.compare_func = self.exact
        # regex match
        elif string.startswith('~'):
            string = string[1:]
            self.compare_func = self.rx_match
        # contains match
        else:
            self.compare_func = self.contains

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
        if self.compare_func == self.rx_match:
            self.regex = re.compile(string)
        else:
            self.filter_str = string

    def __call__(self, cdx):
        if not self.field:
            val = str(cdx)
        else:
            val = str(cdx.get(self.field, ''))

        matched = self.compare_func(val)

        return matched ^ self.invert

    def exact(self, val):
        return (self.filter_str == val)

    def contains(self, val):
        return (self.filter_str in val)

    def rx_match(self, val):
        res = self.regex.match(val)
        return res is not None


#=================================================================
def cdx_filter(cdx_iter, filter_strings):
    """
    filter CDX by regex if each filter is :samp:`{field}:{regex}` form,
    apply filter to :samp:`cdx[{field}]`.
    """
    # Support single strings as well
    if isinstance(filter_strings, str):
        filter_strings = [filter_strings]

    filters = [CDXFilter(filter_str) for filter_str in filter_strings]

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
def cdx_sort_closest(closest, cdx_iter, limit=10, sorted_input=False):
    """
    sort CDXCaptureResult by closest to timestamp.

    yield the `limit` captures nearest to `closest`, nearest first.
    on equal distance, the capture that came first in `cdx_iter` comes first.

    if `sorted_input` is set, `cdx_iter` should be in ascending timestamp
    order, as the captures of a single url are. the scan then stops at the
    first capture after `closest` that is not nearer than the captures kept,
    as no later capture can be nearer. if a capture is found out of order,
    the whole input is scanned.
    """
    closest_sec = timestamp_to_sec(closest)

    # bounded max-heap of the nearest captures so far, the farthest on top:
    # (-distance, -position, cdx). position is unique, so cdx is never compared
    heap = []
    last_sec = None
    scanned = 0

    for pos, cdx in enumerate(cdx_iter):
        scanned += 1
        sec = timestamp_to_sec(cdx[TIMESTAMP])
        key = abs(closest_sec - sec)

        if sorted_input:
            if last_sec is not None and sec < last_sec:
                sorted_input = False
            last_sec = sec

        if len(heap) < limit:
            heappush(heap, (-key, -pos, cdx))

        elif not heap:
            # limit <= 0: keep nothing, but still read the whole input
            continue

        elif key < -heap[0][0]:
            heapreplace(heap, (-key, -pos, cdx))

        elif sorted_input and sec > closest_sec:
            # after closest and not nearer than any capture kept: every
            # later capture is even farther away
            break

    if scanned >= CLOSEST_WARN_CAPTURES:
        # closest may be any string, log the timestamp parsed from it
        logger.warning('Closest lookup read %d captures: key=%s closest=%s limit=%s',
                       scanned, cdx.get(URLKEY), sec_to_timestamp(closest_sec), limit)

    # nearest first, then earliest position first
    heap.sort(reverse=True)

    for _, _, cdx in heap:
        yield cdx


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
