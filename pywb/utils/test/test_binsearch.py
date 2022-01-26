#=================================================================
"""
# binsearch tests

# Prefix Search
>>> print_binsearch_results('org,iana)/domains/root', iter_prefix)
org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz
org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz
org,iana)/domains/root/servers 20140126201227 http://www.iana.org/domains/root/servers text/html 200 AFW34N3S4NK2RJ6QWMVPB5E2AIUETAHU - - 3137 733840 iana.warc.gz

# Exact Search
>>> print_binsearch_results('org,iana)/domains/root', iter_exact)
org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz

>>> print_binsearch_results('org,iana)/', iter_exact)
org,iana)/ 20140126200624 http://www.iana.org/ text/html 200 OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB - - 2258 334 iana.warc.gz

>>> print_binsearch_results('org,iana)/domains/root/db', iter_exact)
org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz

>>> print_binsearch_results('org,iana)/time-zones', iter_exact)
org,iana)/time-zones 20140126200737 http://www.iana.org/time-zones text/html 200 4Z27MYWOSXY2XDRAJRW7WRMT56LXDD4R - - 2449 569675 iana.warc.gz

>>> print_binsearch_results_range('org,iana)/time-zones', 'org,iana)/time-zones!', iter_range)
org,iana)/time-zones 20140126200737 http://www.iana.org/time-zones text/html 200 4Z27MYWOSXY2XDRAJRW7WRMT56LXDD4R - - 2449 569675 iana.warc.gz

# Exact search -- no matches
>>> print_binsearch_results('org,iaana)/', iter_exact)
>>> print_binsearch_results('org,ibna)/', iter_exact)


# Range Search (end exclusive)
>>> print_binsearch_results_range('org,iana)/about', 'org,iana)/domains', iter_range)
org,iana)/about 20140126200706 http://www.iana.org/about text/html 200 6G77LZKFAVKH4PCWWKMW6TRJPSHWUBI3 - - 2962 483588 iana.warc.gz
org,iana)/about/performance/ietf-draft-status 20140126200815 http://www.iana.org/about/performance/ietf-draft-status text/html 302 Y7CTA2QZUSCDTJCSECZNSPIBLJDO7PJJ - - 584 596566 iana.warc.gz
org,iana)/about/performance/ietf-statistics 20140126200804 http://www.iana.org/about/performance/ietf-statistics text/html 302 HNYDN7XRX46RQTT2OFIWXKEYMZQAJWHD - - 582 581890 iana.warc.gz
org,iana)/dnssec 20140126201306 http://www.iana.org/dnssec text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 442 772827 iana.warc.gz
org,iana)/dnssec 20140126201307 https://www.iana.org/dnssec text/html 200 PHLRSX73EV3WSZRFXMWDO6BRKTVUSASI - - 2278 773766 iana.warc.gz


# Range Search -- exact
>>> print_binsearch_results_range('org,iana)/about', 'org,iana)/about!', iter_range)
org,iana)/about 20140126200706 http://www.iana.org/about text/html 200 6G77LZKFAVKH4PCWWKMW6TRJPSHWUBI3 - - 2962 483588 iana.warc.gz

# Range Search -- exact + 1 prev
>>> print_binsearch_results_range('org,iana)/about', 'org,iana)/about!', iter_range, prev_size=1)
org,iana)/_js/2013.1/jquery.js 20140126201307 https://www.iana.org/_js/2013.1/jquery.js warc/revisit - AAW2RS7JB7HTF666XNZDQYJFA6PDQBPO - - 543 778507 iana.warc.gz
org,iana)/about 20140126200706 http://www.iana.org/about text/html 200 6G77LZKFAVKH4PCWWKMW6TRJPSHWUBI3 - - 2962 483588 iana.warc.gz

# Range Search -- exact + 2 prev
>>> print_binsearch_results_range('org,iana)/about', 'org,iana)/about!', iter_range, prev_size=2)
org,iana)/_js/2013.1/jquery.js 20140126201248 http://www.iana.org/_js/2013.1/jquery.js warc/revisit - AAW2RS7JB7HTF666XNZDQYJFA6PDQBPO - - 544 765491 iana.warc.gz
org,iana)/_js/2013.1/jquery.js 20140126201307 https://www.iana.org/_js/2013.1/jquery.js warc/revisit - AAW2RS7JB7HTF666XNZDQYJFA6PDQBPO - - 543 778507 iana.warc.gz
org,iana)/about 20140126200706 http://www.iana.org/about text/html 200 6G77LZKFAVKH4PCWWKMW6TRJPSHWUBI3 - - 2962 483588 iana.warc.gz


# Test at boundary
>>> print_binsearch_results('a)/', iter_exact)
>>> print_binsearch_results_range('a)/', 'a-', iter_range)

>>> print_binsearch_results_range('a)/', 'org,iana)/_css/2013.1/fonts/inconsolata.otf ', iter_range)
org,iana)/ 20140126200624 http://www.iana.org/ text/html 200 OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB - - 2258 334 iana.warc.gz

>>> print_binsearch_results('z)/', iter_exact)
>>> print_binsearch_results_range('z)/', 'z-', iter_range)

>>> print_binsearch_results_range('org,iana)/protocols', 'z-', iter_range)
org,iana)/protocols 20140126200715 http://www.iana.org/protocols text/html 200 IRUJZEUAXOUUG224ZMI4VWTUPJX6XJTT - - 63663 496277 iana.warc.gz
org,iana)/time-zones 20140126200737 http://www.iana.org/time-zones text/html 200 4Z27MYWOSXY2XDRAJRW7WRMT56LXDD4R - - 2449 569675 iana.warc.gz


"""


#=================================================================
import os
from pywb.utils.binsearch import iter_prefix, iter_exact, iter_range
from pywb.utils.merge import merge

from pywb import get_test_dir

#test_cdx_dir = os.path.dirname(os.path.realpath(__file__)) + '/../sample-data/'
test_cdx_dir = get_test_dir() + 'cdx/'

def print_binsearch_results(key, iter_func):
    with open(test_cdx_dir + 'iana.cdx', 'rb') as cdx:
        for line in iter_func(cdx, key.encode('utf-8')):
            print(line.decode('utf-8'))

def print_binsearch_results_range(key, end_key, iter_func, prev_size=0):
    with open(test_cdx_dir + 'iana.cdx', 'rb') as cdx:
        for line in iter_func(cdx, key.encode('utf-8'), end_key.encode('utf-8'), prev_size=prev_size):
            print(line.decode('utf-8'))



def test_rev_merge():
    with open(test_cdx_dir + 'iana.cdx', 'rb') as cdx:
        lines1 = cdx.readlines()

    with open(test_cdx_dir + 'dupes.cdx', 'rb') as cdx:
        lines2 = cdx.readlines()


    # check reverse merge: verify merging of lists, than reversing
    # equals merging with reverse=True of reversed lists
    assert (list(reversed(list(merge(lines1, lines2)))) ==
            list(merge(reversed(lines1), reversed(lines2), reverse=True)))



if __name__ == "__main__":
    import doctest
    doctest.testmod()


