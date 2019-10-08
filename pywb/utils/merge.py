import sys

if sys.version_info >= (3, 5):  #pragma: no cover
    from heapq import merge
else:  #pragma: no cover
    # ported from python 3.5 heapq merge with reverse=True support

    from heapq import heapify, heappop, heapreplace
    from heapq import _heapify_max, _siftup_max

    def _heappop_max(heap):
        """Maxheap version of a heappop."""
        lastelt = heap.pop()    # raises appropriate IndexError if heap is empty
        if heap:
            returnitem = heap[0]
            heap[0] = lastelt
            _siftup_max(heap, 0)
            return returnitem
        return lastelt

    def _heapreplace_max(heap, item):
        """Maxheap version of a heappop followed by a heappush."""
        returnitem = heap[0]    # raises appropriate IndexError if heap is empty
        heap[0] = item
        _siftup_max(heap, 0)
        return returnitem

    def _get_next_iter(it):
        return it.__next__ if hasattr(it, '__next__') else it.next

    def merge(*iterables, **kwargs):
        '''Merge multiple sorted inputs into a single sorted output.
        Similar to sorted(itertools.chain(*iterables)) but returns a generator,
        does not pull the data into memory all at once, and assumes that each of
        the input streams is already sorted (smallest to largest).
        >>> list(merge([1,3,5,7], [0,2,4,8], [5,10,15,20], [], [25]))
        [0, 1, 2, 3, 4, 5, 5, 7, 8, 10, 15, 20, 25]

        If *key* is not None, applies a key function to each element to determine
        its sort order.

        >>> list(merge(['dog', 'horse'], ['cat', 'fish', 'kangaroo'], key=len))
        ['dog', 'cat', 'fish', 'horse', 'kangaroo']
        '''

        key = kwargs.get('key', None)
        reverse = kwargs.get('reverse', False)

        h = []
        h_append = h.append

        if reverse:
            _heapify = _heapify_max
            _heappop = _heappop_max
            _heapreplace = _heapreplace_max
            direction = -1
        else:
            _heapify = heapify
            _heappop = heappop
            _heapreplace = heapreplace
            direction = 1

        if key is None:
            for order, it in enumerate(map(iter, iterables)):
                try:
                    next = _get_next_iter(it)
                    h_append([next(), order * direction, next])
                except StopIteration:
                    pass
            _heapify(h)
            while len(h) > 1:
                try:
                    while True:
                        value, order, next = s = h[0]
                        yield value
                        s[0] = next()           # raises StopIteration when exhausted
                        _heapreplace(h, s)      # restore heap condition
                except StopIteration:
                    _heappop(h)                 # remove empty iterator
            if h:
                # fast case when only a single iterator remains
                value, order, next = h[0]
                yield value
                for v in next.__self__:
                    yield v

            return

        for order, it in enumerate(map(iter, iterables)):
            try:
                next = _get_next_iter(it)
                value = next()
                h_append([key(value), order * direction, value, next])
            except StopIteration:
                pass
        _heapify(h)
        while len(h) > 1:
            try:
                while True:
                    key_value, order, value, next = s = h[0]
                    yield value
                    value = next()
                    s[0] = key(value)
                    s[2] = value
                    _heapreplace(h, s)
            except StopIteration:
                _heappop(h)
        if h:
            key_value, order, value, next = h[0]
            yield value
            for v in next.__self__:
                yield v


