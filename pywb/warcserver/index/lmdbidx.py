"""
Read the secondary index (.idx) of a ZipNum index from an LMDB database,
instead of a binary search over the .idx file. Enabled with the ``lmdb``
option of a ``zipnum`` index::

    index:
      type: zipnum
      path: /data/indexes/collection.idx
      lmdb: lmdb:///data/indexes/idx.lmdb?db=collection

The database is loaded from the .idx file with the ``lmdb-zipnum-idx``
command (:mod:`pywb.indexer.lmdbzipnumidx`). The shards and the .loc file are
used as before, and the .idx file when the database isn't available.

Each .idx line is an LMDB entry. The key is the first field of the line
(``urlkey timestamp``), cut to its first 500 bytes as LMDB keys have at most
511, then a tab and the 8 byte big-endian line number, which keeps the order
of the file and makes the keys of consecutive blocks with the same first
field unique. The value is the rest of the line, so the whole line is the key
without the line number followed by the value, and is compared whole, as in
the binary search over the file.
"""

import itertools
import logging
import os
import struct
import threading
import time

from urllib.parse import parse_qs, unquote, urlsplit

try:
    import lmdb
except ImportError:  # pragma: no cover
    lmdb = None


logger = logging.getLogger(__name__)

# bytes of the first field of the line kept on the key, the rest is on the value
KEY_PREFIX_SIZE = 500

# separates the key prefix from the line number, sorts like the tab after the
# first field of the line
KEY_SEPARATOR = b'\t'

LINENO = struct.Struct('>Q')

KEY_SUFFIX_SIZE = len(KEY_SEPARATOR) + LINENO.size

# max named databases on an environment, e.g. one per ZipNum index
MAX_DBS = 64

# seconds to wait before trying again to open a missing or failed database
RETRY_INTERVAL = 60


# ============================================================================
def idx_entry(line, lineno):
    """ The LMDB (key, value) of an .idx line, without its newline
    """
    first_field = line.partition(b'\t')[0]
    prefix = first_field[:KEY_PREFIX_SIZE]
    return prefix + KEY_SEPARATOR + LINENO.pack(lineno), line[len(prefix):]


def idx_line(key, value):
    """ The .idx line of an LMDB entry, without its newline
    """
    return key[:-KEY_SUFFIX_SIZE] + value


def parse_uri(uri):
    """ The environment path and the named database (or None) of an
    ``lmdb:///path/to/env?db=name`` uri
    """
    parts = urlsplit(uri)
    if parts.scheme != 'lmdb' or parts.netloc or not parts.path:
        raise ValueError('Invalid LMDB uri, expected lmdb:///path/to/env?db=name: ' + uri)

    db_names = parse_qs(parts.query).get('db')
    return unquote(parts.path), db_names[-1] if db_names else None


# ============================================================================
# LMDB can't be used across fork() and an environment must only be opened once
# per process, so each process opens its own, shared by all the indexes

_lock = threading.Lock()

# environment path -> (pid, lmdb.Environment)
_environments = {}

# environments opened before fork(), never closed by the child process, as
# LMDB would release the reader slots of the parent
_inherited = []


def get_environment(env_path):
    """ The read only LMDB environment of this process for env_path
    """
    pid = os.getpid()
    with _lock:
        opened = _environments.get(env_path)
        if opened and opened[0] == pid:
            return opened[1]
        if opened:
            _inherited.append(opened[1])

        # lock: needed to read a consistent snapshot while the loader writes
        # readahead: disabled as lookups are random reads
        env = lmdb.open(env_path, readonly=True, lock=True, readahead=False, max_dbs=MAX_DBS)
        _environments[env_path] = (pid, env)
        return env


def close_environments():
    """ Close the environments opened by this process
    """
    pid = os.getpid()
    with _lock:
        for env_path, (env_pid, env) in list(_environments.items()):
            if env_pid == pid:
                env.close()
                del _environments[env_path]


# ============================================================================
class LMDBIdxReader(object):
    """ The .idx lines of an LMDB named database, on a read transaction.
    Same interface as the .idx file reader of the ZipNumIndexSource
    """
    def __init__(self, txn, db):
        self.txn = txn
        self.db = db

    def search(self, key, prev_size=0):
        """ Like binsearch.search() on the .idx file: the lines from the first
        one >= key, preceded by up to prev_size lines, or without any, the
        last prev_size lines
        """
        cursor = self.txn.cursor(self.db)

        # no key of a line >= key is smaller than the key cut to the size of
        # the key prefix, or before a tab, that sorts first like the separator
        found = cursor.set_range(key[:KEY_PREFIX_SIZE].partition(b'\t')[0])
        while found and idx_line(cursor.key(), cursor.value()) < key:
            found = cursor.next()

        if not found:
            if prev_size and cursor.last():
                last = idx_line(cursor.key(), cursor.value())
                for line in reversed(self._lines_before(cursor, prev_size - 1)):
                    yield line
                yield last
            return

        match = cursor.key()
        for line in reversed(self._lines_before(cursor, prev_size)):
            yield line

        cursor.set_key(match)
        for key, value in cursor:
            yield idx_line(key, value)

    def iter_range(self, start, end, prev_size=0):
        """ Like binsearch.iter_range(): the search() lines < end
        """
        return itertools.takewhile(lambda line: line < end, self.search(start, prev_size))

    def read_last_line(self):
        """ Like read_last_line() on the .idx file, with its newline
        """
        cursor = self.txn.cursor(self.db)
        if not cursor.last():
            # as on an empty .idx file
            raise IndexError('list index out of range')

        return idx_line(cursor.key(), cursor.value()) + b'\n'

    @staticmethod
    def _lines_before(cursor, size):
        lines = []
        while len(lines) < size and cursor.prev():
            lines.append(idx_line(cursor.key(), cursor.value()))
        return lines

    def close(self):
        self.txn.abort()


# ============================================================================
class LMDBIdx(object):
    """ The .idx of a ZipNum index in an LMDB named database, opened read only
    on the first lookup of each process. If the database isn't available or a
    lookup fails, open_reader() returns None, so that the .idx file is used,
    and the database is tried again after RETRY_INTERVAL seconds
    """
    def __init__(self, uri, summary=None):
        if lmdb is None:
            raise ImportError('The lmdb option of a zipnum index needs the lmdb package: pip install lmdb')

        env_path, self.db_name = parse_uri(uri)
        if not self.db_name:
            raise ValueError('The LMDB .idx needs a named database, lmdb:///path/to/env?db=name: ' + uri)

        self.uri = uri
        self.summary = summary
        self.env_path = os.path.abspath(env_path)
        self._db = None
        self._db_pid = None
        self._retry_at = 0

    def open_reader(self):
        """ A reader of the .idx on a new read transaction, or None if the
        database isn't available
        """
        opened = self._open()
        if not opened:
            return None

        env, db = opened
        try:
            try:
                txn = env.begin(db=db)
            except lmdb.MapResizedError:
                # the loader grew the database map, adopt the new size
                env.set_mapsize(0)
                txn = env.begin(db=db)
        except lmdb.Error as e:
            self._fail('lookup failed', e)
            return None

        return LMDBIdxReader(txn, db)

    def _open(self):
        pid = os.getpid()
        if self._db is not None and self._db_pid == pid:
            return self._db

        if time.monotonic() < self._retry_at:
            return None

        try:
            env = get_environment(self.env_path)
            db = env.open_db(self.db_name.encode('utf-8'), create=False)
        except lmdb.Error as e:
            self._fail('not available', e)
            return None

        self._db = (env, db)
        self._db_pid = pid
        return self._db

    def _fail(self, reason, error):
        self._db = None
        self._retry_at = time.monotonic() + RETRY_INTERVAL
        logger.warning('LMDB .idx %s %s, using %s, retrying in %s s: %s',
                       self.uri, reason, self.summary, RETRY_INTERVAL, error)

    def __repr__(self):
        return 'LMDBIdx({0})'.format(self.uri)
