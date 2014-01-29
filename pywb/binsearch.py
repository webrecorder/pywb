from collections import deque
import os
import itertools

class FileReader:
    def __init__(self, filename):
        self.fh = open(filename, 'rb')
        self.filename = filename
        self.size = os.path.getsize(filename)

    def getsize(self):
        return self.size

    def readline(self):
        return self.fh.readline()

    def seek(self, offset):
        return self.fh.seek(offset)

    def close(self):
        return self.fh.close()


def binsearch_offset(reader, key, compare_func = cmp, block_size = 8192):
    min = 0
    max = reader.getsize() / block_size

    while (max - min > 1):
        mid = min + ((max - min) / 2)
        reader.seek(mid * block_size)

        if mid > 0:
            reader.readline() # skip partial line

        line = reader.readline()

        if compare_func(key, line) > 0:
            min = mid
        else:
            max = mid

    return (min * block_size)


def search(reader, key, prev_size = 0, compare_func = cmp, block_size = 8192):
    min = binsearch_offset(reader, key, compare_func, block_size)

    reader.seek(min)

    if min > 0:
        reader.readline() # skip partial line

    if prev_size > 1:
        prev_deque = deque(maxlen = prev_size)

    line = None

    while True:
        line = reader.readline()
        if not line:
            break
        if compare_func(line, key) >= 0:
            break

        if prev_size == 1:
            prev = line
        elif prev_size > 1:
            prev_deque.append(line)

    def gen_iter(line):
        if prev_size == 1:
            yield prev.rstrip()
        elif prev_size > 1:
            for i in prev_deque:
                yield i.rstrip()

        while line:
            yield line.rstrip()
            line = reader.readline()

    return gen_iter(line)


# Iterate over prefix matches
def iter_prefix(reader, key):
    """
    >>> print_test_cdx('org,iana)/domains/root', iter_prefix)
    org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz
    org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
    org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz
    org,iana)/domains/root/servers 20140126201227 http://www.iana.org/domains/root/servers text/html 200 AFW34N3S4NK2RJ6QWMVPB5E2AIUETAHU - - 3137 733840 iana.warc.gz
    """

    lines = search(reader, key)
    return itertools.takewhile(lambda line: line.startswith(key), lines)


def iter_exact(reader, key, tok = ' '):
    """
    >>> print_test_cdx('org,iana)/domains/root', iter_exact)
    org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz

    >>> print_test_cdx('org,iana)/', iter_exact)
    org,iana)/ 20140126200624 http://www.iana.org/ text/html 200 OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB - - 2258 334 iana.warc.gz

    >>> print_test_cdx('org,iana)/domains/root/db', iter_exact)
    org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
    org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz

    >>> print_test_cdx('org,iaana)/', iter_exact)
    >>> print_test_cdx('org,ibna)/', iter_exact)

    >>> print_test_cdx('org,iana)/time-zones', iter_exact)
    org,iana)/time-zones 20140126200737 http://www.iana.org/time-zones text/html 200 4Z27MYWOSXY2XDRAJRW7WRMT56LXDD4R - - 2449 569675 iana.warc.gz
    """

    lines = search(reader, key)

    def check_key(line):
        line_key = line.split(tok, 1)[0]
        return line_key == key

    return itertools.takewhile(check_key, lines)


import utils
if __name__ == "__main__" or utils.enable_doctests():

    def create_test_cdx(test_file):
        path = utils.test_data_dir() + 'cdx/' + test_file
        return FileReader(path)

    test_cdx = create_test_cdx('iana.cdx')

    def print_test_cdx(key, iter_func, filename = None):
        cdx = test_cdx if not filename else create_test_cdx(filename)
        for line in iter_func(cdx, key):
            print line

        #cdx.close()

    import doctest
    doctest.testmod()




