import binsearch
import indexreader
import bisect
import itertools
import re

from heapq import merge
from collections import deque

class LocalCDXServer:
    def __init__(sources):
        self.sources = sources

    pass


def merge_sort_streams(sources, key, iter_func):
    """
    >>> test_cdx(key = 'org,iana)/', sources = ['dupes.cdx', 'iana.cdx'])
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
    """

    # optimize for single last
    if limit == 1:
        last = None

        for cdx in cdx_iter:
            last = cdx

        return [last]

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
# sort cdx by closest to timestamp
def cdx_collapse_time(cdx_iter, timelen = 10):
    """
    >>> test_cdx(key = 'org,iana)/_css/2013.1/screen.css', collapse_time = 11)
    org,iana)/_css/2013.1/screen.css 20140126200625 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 8754 41238 iana.warc.gz
    org,iana)/_css/2013.1/screen.css 20140126201054 http://www.iana.org/_css/2013.1/screen.css warc/revisit - BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 543 706476 iana.warc.gz


    >>> test_cdx(key = 'org,iana)/_css/2013.1/screen.css', collapse_time = 11, resolve_revisits = True)
    org,iana)/_css/2013.1/screen.css 20140126200625 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 8754 41238 iana.warc.gz - - -
    org,iana)/_css/2013.1/screen.css 20140126201054 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 543 706476 iana.warc.gz 8754 41238 iana.warc.gz

    """

    last_dedup_time = None

    for cdx in cdx_iter:
        curr_dedup_time = cdx['timestamp'][:timelen]

        # yield if last_dedup_time is diff, otherwise skip
        if curr_dedup_time != last_dedup_time:
            last_dedup_time = curr_dedup_time
            yield cdx



#=================================================================
# sort CDXCaptureResult by closest to timestamp
def cdx_sort_closest(closest, cdx_iter, limit = 10):
    """
    >>> test_cdx(closest_to = '20140126200826', key = 'org,iana)/_css/2013.1/fonts/opensans-bold.ttf', timestamp_only = True)
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

    # equal dist prefer earlier
    >>> test_cdx(closest_to = '20140126200700', key = 'org,iana)/_css/2013.1/fonts/opensans-bold.ttf', resolve_revisits = True, timestamp_only = False, limit = 2)
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200654 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 548 482544 iana.warc.gz 117166 198285 iana.warc.gz
    org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200706 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 552 495230 iana.warc.gz 117166 198285 iana.warc.gz

    >>> test_cdx(closest_to = '20140126200659', key = 'org,iana)/_css/2013.1/fonts/opensans-bold.ttf', resolve_revisits = True, timestamp_only = True, limit = 2)
    20140126200654
    20140126200706

    >>> test_cdx(closest_to = '20140126200701', key = 'org,iana)/_css/2013.1/fonts/opensans-bold.ttf', resolve_revisits = True, timestamp_only = True, limit = 2)
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

    test_dir = os.path.dirname(os.path.realpath(__file__)) + '/../test/'

    def create_test_cdx(test_file):
        path = os.path.dirname(os.path.realpath(__file__)) + '/../test/' + test_file
        return binsearch.FileReader(path)

    def wrap_test_path(filenames):
        return map(lambda x: test_dir + x, filenames)

    test_cdx_iter = create_test_cdx('iana.cdx')

    def test_cdx(key,
                 closest_to = None,
                 limit = 10,
                 collapse_time = None,
                 timestamp_only = False,
                 resolve_revisits = False,
                 reverse = False,
                 filters = None,
                 sources = ['iana.cdx'],
                 match_func = binsearch.iter_exact):

        cdx_iter = merge_sort_streams(wrap_test_path(sources), key, match_func)

        cdx_iter = make_cdx_iter(cdx_iter)

        if resolve_revisits:
            cdx_iter = cdx_resolve_revisits(cdx_iter)

        if filters:
            cdx_iter = cdx_filter(cdx_iter, filters)

        if collapse_time:
            cdx_iter = cdx_collapse_time(cdx_iter, collapse_time)

        if reverse:
            cdx_iter = cdx_reverse(cdx_iter, limit)

        if closest_to:
            cdx_iter = cdx_sort_closest(closest_to, cdx_iter, limit)

        if limit:
            cdx_iter = cdx_limit(cdx_iter, limit)

        for cdx in cdx_iter:
            print cdx['timestamp'] if timestamp_only else cdx



    import doctest
    doctest.testmod()


