from cdxobject import CDXObject

from ..binsearch.binsearch import iter_exact, iter_prefix, FileReader

import timeutils
import bisect
import itertools
import re

from heapq import merge
from collections import deque



#=================================================================
def cdx_text_out(cdx, fields):
    if not fields:
        return str(cdx)
    else:
        return ' '.join(map(lambda x: cdx[x], fields.split(',')))


#=================================================================
def cdx_load(sources, params):
    cdx_iter = load_cdx_streams(sources, params)

    cdx_iter = make_cdx_iter(cdx_iter)

    resolve_revisits = params.get('resolve_revisits', False)
    if resolve_revisits:
        cdx_iter = cdx_resolve_revisits(cdx_iter)

    filters = params.get('filter', None)
    if filters:
        cdx_iter = cdx_filter(cdx_iter, filters)

    collapse_time = params.get('collapse_time', None)
    if collapse_time:
        cdx_iter = cdx_collapse_time_status(cdx_iter, collapse_time)

    limit = int(params.get('limit', 1000000))

    reverse = params.get('reverse', False)
    if reverse:
        cdx_iter = cdx_reverse(cdx_iter, limit)

    closest_to = params.get('closest_to', None)
    if closest_to:
        cdx_iter = cdx_sort_closest(closest_to, cdx_iter, limit)

    if limit:
        cdx_iter = cdx_limit(cdx_iter, limit)

    # output raw cdx objects
    if params.get('output') == 'raw':
        return cdx_iter

    def write_cdx(fields):
        for cdx in cdx_iter:
            yield cdx_text_out(cdx, fields) + '\n'

    return write_cdx(params.get('fields'))


#=================================================================
# load and source merge cdx streams
def load_cdx_streams(sources, params):
    # Optimize: no need to merge if just one input
    if len(sources) == 1:
        return sources[0].load_cdx(params)

    source_iters = map(lambda src: src.load_cdx(params), sources)
    merged_stream = merge(*(source_iters))
    return merged_stream

#=================================================================
# convert text cdx stream to CDXObject
def make_cdx_iter(text_iter):
    return itertools.imap(lambda line: CDXObject(line), text_iter)


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

    reverse_cdxs = deque(maxlen = limit)

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

            parts = string.split(':', 1)
            # no field set, apply filter to entire cdx
            if len(parts) == 1:
                self.field = ''
            else:
            # apply filter to cdx[field]
                self.field = parts[0]
                string = parts[1]

            self.regex = re.compile(string)

        def __call__(self, cdx):
            val = cdx[self.field] if self.field else str(cdx)
            matched = self.regex.match(val) is not None
            return matched ^ self.invert

    filters = map(Filter, filter_strings)

    for cdx in cdx_iter:
        if all (x(cdx) for x in filters):
            yield cdx



#=================================================================
# collapse by timestamp and status code
def cdx_collapse_time_status(cdx_iter, timelen = 10):
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
def cdx_sort_closest(closest, cdx_iter, limit = 10):
    closest_cdx = []

    closest_sec = timeutils.timestamp_to_sec(closest)

    for cdx in cdx_iter:
        sec = timeutils.timestamp_to_sec(cdx['timestamp'])
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
        is_revisit = (cdx['mimetype'] == 'warc/revisit') or (cdx['filename'] == '-')

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


