from collections import deque
import os
import itertools

class FileReader:
    def __init__(self, filename):
        self.fh = open(filename, 'rb')
        self.size = os.path.getsize(filename)

    def getsize(self):
        return self.size

    def readline(self):
        return self.fh.readline()

    def seek(self, offset):
        return self.fh.seek(offset)


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
            yield prev
        elif prev_size > 1:
            for i in prev_deque:
                yield i

        while line:
            yield line
            line = reader.readline()

    return gen_iter(line)


# Iterate over exact matches
def iter_exact(reader, key):
    lines = search(reader, key)
    for x in lines:
        if not x.startswith(key):
            break

        yield x





