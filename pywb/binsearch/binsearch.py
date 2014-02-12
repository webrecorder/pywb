from collections import deque
import os
import itertools

#=================================================================
# Binary Search over a text file
#=================================================================
class FileReader:
    """
    A very simple file-like object wrapper that knows it's size
    getsize() method returns the filesize
    """
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


#=================================================================
def binsearch_offset(reader, key, compare_func=cmp, block_size=8192):
    """
    Find offset of the full line which matches a given 'key' using binary search
    If key is not found, the offset is of the line after the key

    File is subdivided into block_size (default 8192) sized blocks
    Optional compare_func may be specified
    """
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
    """
    Perform a binsearch for a specified key down to block_size (8192) sized blocks,
    followed by linear search within the block to find first matching line.

    When performing linear search, keep track of up to N previous lines before
    first matching line.
    """
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
    Creates an iterator which iterates over prefix matches for a key in a sorted text file
    A line matches as long as it starts with key
    """

    return itertools.takewhile(lambda line: line.startswith(key), search(reader, key))


def iter_exact(reader, key, token=' '):
    """
    Create an iterator which iterates over exact matches for a key in a sorted text file
    Key is terminated by a token (default ' ')
    """

    return iter_prefix(reader, key + token)

