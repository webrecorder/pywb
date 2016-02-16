"""
Utility functions for performing binary search over a sorted text file
"""

from collections import deque
import itertools
import six

import sys

if six.PY3:
    def cmp(a, b):
        return (a > b) - (a < b)


#=================================================================
def binsearch_offset(reader, key, compare_func=cmp, block_size=8192):
    """
    Find offset of the line which matches a given 'key' using binary search
    If key is not found, the offset is of the line after the key

    File is subdivided into block_size (default 8192) sized blocks
    Optional compare_func may be specified
    """
    min_ = 0

    reader.seek(0, 2)
    max_ = int(reader.tell() / block_size)

    while max_ - min_ > 1:
        mid = int(min_ + ((max_ - min_) / 2))
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
def binsearch(reader, key, compare_func=cmp, block_size=8192):
    """
    Perform a binary search for a specified key to within a 'block_size'
    (default 8192) granularity, and return first full line found.
    """

    min_ = binsearch_offset(reader, key, compare_func, block_size)

    reader.seek(min_)

    if min_ > 0:
        reader.readline()  # skip partial line

    def gen_iter(line):
        while line:
            yield line.rstrip()
            line = reader.readline()

    return gen_iter(reader.readline())


#=================================================================
def linearsearch(iter_, key, prev_size=0, compare_func=cmp):
    """
    Perform a linear search over iterator until
    current_line >= key

    optionally also tracking upto N previous lines, which are
    returned before the first matched line.

    if end of stream is reached before a match is found,
    nothing is returned (prev lines discarded also)
    """

    prev_deque = deque(maxlen=prev_size + 1)

    matched = False

    for line in iter_:
        prev_deque.append(line)
        if compare_func(line, key) >= 0:
            matched = True
            break

    # no matches, so return empty iterator
    if not matched:
        return iter([])

    return itertools.chain(prev_deque, iter_)


#=================================================================
def search(reader, key, prev_size=0, compare_func=cmp, block_size=8192):
    """
    Perform a binary search for a specified key to within a 'block_size'
    (default 8192) sized block followed by linear search
    within the block to find first matching line.

    When performin_g linear search, keep track of up to N previous lines before
    first matching line.
    """
    iter_ = binsearch(reader, key, compare_func, block_size)
    iter_ = linearsearch(iter_,
                         key, prev_size=prev_size,
                         compare_func=compare_func)
    return iter_


#=================================================================
def iter_range(reader, start, end, prev_size=0):
    """
    Creates an iterator which iterates over lines where
    start <= line < end (end exclusive)
    """

    iter_ = search(reader, start, prev_size=prev_size)

    end_iter = itertools.takewhile(
        lambda line: line < end,
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
def iter_exact(reader, key, token=b' '):
    """
    Create an iterator which iterates over lines where the first field matches
    the 'key', equivalent to token + sep prefix.
    Default field termin_ator/seperator is ' '
    """

    return iter_prefix(reader, key + token)
