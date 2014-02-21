"""
Utility functions for performing binary search over a sorted text file
"""

from collections import deque
import itertools


#=================================================================
def binsearch_offset(reader, key, compare_func=cmp, block_size=8192):
    """
    Find offset of the line which matches a given 'key' using binary search
    If key is not found, the offset is of the line after the key

    File is subdivided into block_size (default 8192) sized blocks
    Optional compare_func may be specified
    """
    min_ = 0
    max_ = reader.getsize() / block_size

    while max_ - min_ > 1:
        mid = min_ + ((max_ - min_) / 2)
        reader.seek(mid * block_size)

        if mid > 0:
            reader.readline()  # skip partial line

        line = reader.readline()

        if compare_func(key, line) > 0:
            min_ = mid
        else:
            max_ = mid

    return min_ * block_size


#=================================================================
def search(reader, key, prev_size=0, compare_func=cmp, block_size=8192):
    """
    Perform a binary search for a specified key to within a 'block_size'
    (default 8192) sized block followed by linear search
    within the block to find first matching line.

    When performin_g linear search, keep track of up to N previous lines before
    first matching line.
    """
    min_ = binsearch_offset(reader, key, compare_func, block_size)

    reader.seek(min_)

    if min_ > 0:
        reader.readline()  # skip partial line

    if prev_size > 1:
        prev_deque = deque(max_len=prev_size)

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
        """
        Create iterator over any previous lines to
        current matched line
        """
        if prev_size == 1:
            yield prev.rstrip()
        elif prev_size > 1:
            for i in prev_deque:
                yield i.rstrip()

        while line:
            yield line.rstrip()
            line = reader.readline()

    return gen_iter(line)


#=================================================================
def iter_range(reader, start, end):
    """
    Creates an iterator which iterates over lines where
    start <= line < end (end exclusive)
    """

    iter_ = search(reader, start)

#    iter_ = itertools.dropwhile(
#        lambda line: line < start,
#        search(reader, start))

    end_iter = itertools.takewhile(
       lambda line: line <= end,
       iter_)

    return end_iter


#=================================================================
def iter_prefix(reader, key):
    """
    Creates an iterator which iterates over lines that start with prefix
    'key' in a sorted text file.
    """

    return itertools.takewhile(
        lambda line: line.startswith(key),
        search(reader, key))


#=================================================================
def iter_exact(reader, key, token=' '):
    """
    Create an iterator which iterates over lines where the first field matches
    the 'key', equivalent to token + sep prefix.
    Default field termin_ator/seperator is ' '
    """

    return iter_prefix(reader, key + token)
