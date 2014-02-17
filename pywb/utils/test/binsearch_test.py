#=================================================================
"""
# binsearch tests

# Prefix Search
>>> print_binsearch_results('org,iana)/domains/root', iter_prefix)
org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz
org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz
org,iana)/domains/root/servers 20140126201227 http://www.iana.org/domains/root/servers text/html 200 AFW34N3S4NK2RJ6QWMVPB5E2AIUETAHU - - 3137 733840 iana.warc.gz

>>> print_binsearch_results('org,iana)/domains/root', iter_exact)
org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz

>>> print_binsearch_results('org,iana)/', iter_exact)
org,iana)/ 20140126200624 http://www.iana.org/ text/html 200 OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB - - 2258 334 iana.warc.gz

>>> print_binsearch_results('org,iana)/domains/root/db', iter_exact)
org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz

# Exact Search
>>> print_binsearch_results('org,iaana)/', iter_exact)
>>> print_binsearch_results('org,ibna)/', iter_exact)

>>> print_binsearch_results('org,iana)/time-zones', iter_exact)
org,iana)/time-zones 20140126200737 http://www.iana.org/time-zones text/html 200 4Z27MYWOSXY2XDRAJRW7WRMT56LXDD4R - - 2449 569675 iana.warc.gz
"""


#=================================================================
import os
from pywb.utils.binsearch import iter_prefix, iter_exact
from pywb.utils.loaders import SeekableTextFileReader

from pywb import get_test_dir

#test_cdx_dir = os.path.dirname(os.path.realpath(__file__)) + '/../sample-data/'
test_cdx_dir = get_test_dir() + 'cdx/'

def print_binsearch_results(key, iter_func):
    cdx =  SeekableTextFileReader(test_cdx_dir + 'iana.cdx')

    for line in iter_func(cdx, key):
        print line


if __name__ == "__main__":
    import doctest
    doctest.testmod()


