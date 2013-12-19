import itertools

def peek_iter(iterable):
    try:
        first = next(iterable)
    except StopIteration:
        return None

    return itertools.chain([first], iterable)
