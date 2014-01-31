import binsearch
import indexreader
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
def cdx_serve(key, params, sources, match_func = binsearch.iter_exact):
    cdx_iter = merge_sort_streams(sources, key, match_func)

    cdx_iter = make_cdx_iter(cdx_iter)

    resolve_revisits = params.get('resolve_revisits', False)
    if resolve_revisits:
        cdx_iter = cdx_resolve_revisits(cdx_iter)

    filters = params.get('filters', None)
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
# merge multiple cdx streams
def merge_sort_streams(sources, key, iter_func):
    """
    >>> test_cdx(key = 'org,iana)/', sources = [test_dir + 'dupes.cdx', test_dir + 'iana.cdx'])
    org,iana)/ 20140126200624 http://www.iana.org/ text/html 200 OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB - - 2258 334 iana.warc.gz
    org,iana)/ 20140127171238 http://iana.org unk 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 343 1858 dupes.warc.gz
    org,iana)/ 20140127171238 http://www.iana.org/ warc/revisit - OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB - - 536 2678 dupes.warc.gz
    """

    def load_src(source):
        source = binsearch.FileReader(source)
        source = iter_func(source, key)
        return source

    # Optimize: no need to merge if just one input
    if len(sources) == 1:
        return load_src(sources[0])

    source_iters = map(load_src, sources)
    merged_stream = merge(*(source_iters))
    return merged_stream

#=================================================================
# convert text cdx stream to CDXCaptureResult
def make_cdx_iter(text_iter):
    return itertools.imap(lambda line: indexreader.CDXCaptureResult(line), text_iter)


#=================================================================
# limit cdx to at most limit
def cdx_limit(cdx_iter, limit):
    """
    >>> test_cdx('org,iana)/_css/2013.1/fonts/opensans-bold.ttf', limit = 3)
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200625 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 117166 198285 iana.warc.gz
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200654 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf warc/revisit - YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 548 482544 iana.warc.gz
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200706 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf warc/revisit - YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 552 495230 iana.warc.gz

    """

    for cdx, _ in itertools.izip(cdx_iter, xrange(limit)):
        yield cdx


#=================================================================
# reverse cdx
def cdx_reverse(cdx_iter, limit):
    """
    >>> test_cdx('org,iana)/_css/2013.1/fonts/opensans-bold.ttf', reverse = True, resolve_revisits = True, limit = 3)
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126201308 https://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 551 783712 iana.warc.gz 117166 198285 iana.warc.gz
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126201249 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 552 771773 iana.warc.gz 117166 198285 iana.warc.gz
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126201240 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 551 757988 iana.warc.gz 117166 198285 iana.warc.gz

    >>> test_cdx('org,iana)/_js/2013.1/jquery.js', reverse = True, resolve_revisits = True, limit = 1)
    org,iana)/_js/2013.1/jquery.js 20140126201307 https://www.iana.org/_js/2013.1/jquery.js application/x-javascript 200 AAW2RS7JB7HTF666XNZDQYJFA6PDQBPO - - 543 778507 iana.warc.gz 33449 7311 iana.warc.gz

    # no match, single result
    >>> test_cdx('org,iana)/dont_have_this', reverse = True, resolve_revisits = True, limit = 1)
    """

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
    """
    >>> test_cdx(key = 'org,iana)/domains', match_func = binsearch.iter_prefix, filters = ['mimetype:text/html'])
    org,iana)/domains 20140126200825 http://www.iana.org/domains text/html 200 7UPSCLNWNZP33LGW6OJGSF2Y4CDG4ES7 - - 2912 610534 iana.warc.gz
    org,iana)/domains/arpa 20140126201248 http://www.iana.org/domains/arpa text/html 200 QOFZZRN6JIKAL2JRL6ZC2VVG42SPKGHT - - 2939 759039 iana.warc.gz
    org,iana)/domains/idn-tables 20140126201127 http://www.iana.org/domains/idn-tables text/html 200 HNCUFTJMOQOGAEY6T56KVC3T7TVLKGEW - - 8118 715878 iana.warc.gz
    org,iana)/domains/int 20140126201239 http://www.iana.org/domains/int text/html 200 X32BBNNORV4SPEHTQF5KI5NFHSKTZK6Q - - 2482 746788 iana.warc.gz
    org,iana)/domains/reserved 20140126201054 http://www.iana.org/domains/reserved text/html 200 R5AAEQX5XY5X5DG66B23ODN5DUBWRA27 - - 3573 701457 iana.warc.gz
    org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz
    org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
    org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz
    org,iana)/domains/root/servers 20140126201227 http://www.iana.org/domains/root/servers text/html 200 AFW34N3S4NK2RJ6QWMVPB5E2AIUETAHU - - 3137 733840 iana.warc.gz
    """

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
    """
    # unresolved revisits, different statuscode results in an extra repeat
    >>> test_cdx(key = 'org,iana)/_css/2013.1/screen.css', collapse_time = 11)
    org,iana)/_css/2013.1/screen.css 20140126200625 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 8754 41238 iana.warc.gz
    org,iana)/_css/2013.1/screen.css 20140126200653 http://www.iana.org/_css/2013.1/screen.css warc/revisit - BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 533 328367 iana.warc.gz
    org,iana)/_css/2013.1/screen.css 20140126201054 http://www.iana.org/_css/2013.1/screen.css warc/revisit - BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 543 706476 iana.warc.gz

    # resolved revisits
    >>> test_cdx(key = 'org,iana)/_css/2013.1/screen.css', collapse_time = 11, resolve_revisits = True)
    org,iana)/_css/2013.1/screen.css 20140126200625 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 8754 41238 iana.warc.gz - - -
    org,iana)/_css/2013.1/screen.css 20140126201054 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 543 706476 iana.warc.gz 8754 41238 iana.warc.gz

    """

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
    """
    >>> test_cdx(closest_to = '20140126200826', key = 'org,iana)/_css/2013.1/fonts/opensans-bold.ttf', fields = 'timestamp', limit = 10)
    20140126200826
    20140126200816
    20140126200805
    20140126200912
    20140126200738
    20140126200930
    20140126200718
    20140126200706
    20140126200654
    20140126200625

    >>> test_cdx(closest_to = '20140126201306', key = 'org,iana)/dnssec', resolve_revisits = True, sources = [test_dir + 'dupes.cdx', test_dir + 'iana.cdx'])
    org,iana)/dnssec 20140126201306 http://www.iana.org/dnssec text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 442 772827 iana.warc.gz - - -
    org,iana)/dnssec 20140126201307 https://www.iana.org/dnssec text/html 200 PHLRSX73EV3WSZRFXMWDO6BRKTVUSASI - - 2278 773766 iana.warc.gz - - -


    >>> test_cdx(closest_to = '20140126201307', key = 'org,iana)/dnssec', resolve_revisits = True)
    org,iana)/dnssec 20140126201307 https://www.iana.org/dnssec text/html 200 PHLRSX73EV3WSZRFXMWDO6BRKTVUSASI - - 2278 773766 iana.warc.gz - - -
    org,iana)/dnssec 20140126201306 http://www.iana.org/dnssec text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 442 772827 iana.warc.gz - - -

    # equal dist prefer earlier
    >>> test_cdx(closest_to = '20140126200700', key = 'org,iana)/_css/2013.1/fonts/opensans-bold.ttf', resolve_revisits = True, limit = 2)
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200654 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 548 482544 iana.warc.gz 117166 198285 iana.warc.gz
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200706 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 552 495230 iana.warc.gz 117166 198285 iana.warc.gz

    >>> test_cdx(closest_to = '20140126200659', key = 'org,iana)/_css/2013.1/fonts/opensans-bold.ttf', resolve_revisits = True, limit = 2, fields = 'timestamp')
    20140126200654
    20140126200706

    >>> test_cdx(closest_to = '20140126200701', key = 'org,iana)/_css/2013.1/fonts/opensans-bold.ttf', resolve_revisits = True, limit = 2, fields = 'timestamp')
    20140126200706
    20140126200654

    """
    closest_cdx = []

    closest_sec = utils.timestamp_to_sec(closest)

    for cdx in cdx_iter:
        sec = utils.timestamp_to_sec(cdx['timestamp'])
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
    """
    >>> test_cdx('org,iana)/_css/2013.1/fonts/inconsolata.otf', resolve_revisits = True)
    org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200826 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 34054 620049 iana.warc.gz - - -
    org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200912 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 546 667073 iana.warc.gz 34054 620049 iana.warc.gz
    org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200930 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 534 697255 iana.warc.gz 34054 620049 iana.warc.gz
    org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126201055 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 547 714833 iana.warc.gz 34054 620049 iana.warc.gz
    org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126201249 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 551 768625 iana.warc.gz 34054 620049 iana.warc.gz

    >>> test_cdx('org,iana)/domains/root/db', resolve_revisits = True)
    org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz - - -
    org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz - - -
    """


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





import utils
if __name__ == "__main__" or utils.enable_doctests():
    import os
    import sys

    test_dir = utils.test_data_dir() + 'cdx/'

    def test_cdx(key, match_func = binsearch.iter_exact, sources = [test_dir + 'iana.cdx'], **kwparams):
        for x in cdx_serve(key, kwparams, sources, match_func):
            sys.stdout.write(x)


    import doctest
    doctest.testmod()


