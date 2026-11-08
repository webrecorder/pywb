"""
Load path index files into an LMDB database, to resolve the WARC filenames
with ``archive_paths: lmdb:///path/to/env?db=name`` (LMDBResolver)

Each line of a path index has a WARC filename and its paths (or urls),
separated by tabs. Each named database of the LMDB environment maps the
WARC filename to the tab-separated list of its paths.

Loading adds the new WARC filenames and replaces the paths of the existing
ones, keeping the others, so it can be run once for each new or updated path
index. ``--drop`` empties the database first.

Each run is a single LMDB write transaction: pywb keeps reading the previous
version of the database until it is committed, also with ``--drop``.
The other databases of the environment are not changed.
"""

import os
import re
import sys

from argparse import ArgumentParser, RawTextHelpFormatter

# optional, only needed for lmdb:// archive paths
try:
    import lmdb
except ImportError:  # pragma: no cover
    lmdb = None

from pywb.warcserver.resource.pathresolvers import LMDBResolver


GIB = 1024 ** 3

# LMDB reserves the address space, but only the data uses disk space
DEFAULT_MAP_SIZE_GIB = 64


#=================================================================
class LoadStats(object):
    FIELDS = ('files', 'lines', 'skipped', 'unsorted', 'keys',
              'added', 'updated', 'unchanged', 'dropped')

    def __init__(self, **kwargs):
        for name in self.FIELDS:
            setattr(self, name, kwargs.get(name, 0))

    def __iadd__(self, other):
        for name in self.FIELDS:
            setattr(self, name, getattr(self, name) + getattr(other, name))
        return self

    def __str__(self):
        return ', '.join('{0}={1}'.format(name, getattr(self, name)) for name in self.FIELDS)


#=================================================================
def find_files(paths, pattern=None):
    """ Return the files of paths, and the files of the directories of paths
    whose name fully matches the pattern regex
    """
    regex = re.compile(pattern) if pattern else None
    files = []
    for path in paths:
        if os.path.isdir(path):
            names = sorted(name for name in os.listdir(path)
                           if os.path.isfile(os.path.join(path, name)) and
                           (not regex or regex.fullmatch(name)))

            files.extend(os.path.join(path, name) for name in names)

        elif os.path.isfile(path):
            files.append(path)

        else:
            raise IOError('Path index not found: ' + path)

    return files


def iter_path_index(reader, stats):
    """ Yield the (filename, paths) of a sorted path index, as bytes

    The lines are parsed like PathIndexResolver: trailing whitespace is
    removed and the paths of consecutive lines of the same filename are
    joined. Lines without paths, or with a filename too long for LMDB, are
    skipped.
    """
    key = value = prev_key = None
    for line in reader:
        stats.lines += 1
        line = line.rstrip()
        line_key, sep, line_value = line.partition(b'\t')
        if not sep or not line_key or len(line_key) > LMDBResolver.MAX_KEY_SIZE:
            stats.skipped += 1
            continue

        if prev_key is not None and line_key < prev_key:
            stats.unsorted += 1

        prev_key = line_key

        if line_key == key:
            value += b'\t' + line_value
            continue

        if key is not None:
            yield key, value

        key, value = line_key, line_value

    if key is not None:
        yield key, value


def load(env_path, db_name, paths, pattern=None, drop=False, dry_run=False,
         map_size=DEFAULT_MAP_SIZE_GIB * GIB, out=None):
    """ Load the path index files of paths into the db_name database of
    the env_path LMDB environment, and return the LoadStats
    """
    if lmdb is None:
        raise ImportError('The lmdb package is required, install it with: pip install lmdb')

    if not db_name:
        raise ValueError('The LMDB named database is required')

    files = find_files(paths, pattern)
    name = db_name.encode('utf-8')
    out = out or sys.stdout

    if dry_run:
        return _load_dry_run(env_path, name, files, drop, out)

    env = lmdb.open(env_path, map_size=map_size, max_dbs=LMDBResolver.MAX_DBS, readahead=False)
    try:
        db = env.open_db(name)
        with env.begin(write=True, db=db) as txn:
            return _load_files(txn, db, files, drop, False, out)
    finally:
        env.close()


def _load_dry_run(env_path, name, files, drop, out):
    if not os.path.exists(os.path.join(env_path, 'data.mdb')):
        return _load_files(None, None, files, drop, True, out)

    env = lmdb.open(env_path, readonly=True, max_dbs=LMDBResolver.MAX_DBS, readahead=False)
    try:
        try:
            db = env.open_db(name, create=False)
        except lmdb.NotFoundError:
            return _load_files(None, None, files, drop, True, out)

        with env.begin(db=db) as txn:
            return _load_files(txn, db, files, drop, True, out)
    finally:
        env.close()


def _load_files(txn, db, files, drop, dry_run, out):
    total = LoadStats()
    prefix = '[dry-run] ' if dry_run else ''

    if drop and txn:
        total.dropped = txn.stat(db)['entries']
        if not dry_run:
            txn.drop(db, delete=False)

        out.write('{0}dropped {1} entries\n'.format(prefix, total.dropped))

    for path in files:
        stats = LoadStats(files=1)
        with open(path, 'rb') as reader:
            for key, value in iter_path_index(reader, stats):
                stats.keys += 1
                old = txn.get(key) if txn and not (drop and dry_run) else None
                if old is None:
                    stats.added += 1
                elif old == value:
                    stats.unchanged += 1
                    continue
                else:
                    stats.updated += 1

                if not dry_run:
                    txn.put(key, value)

        out.write('{0}{1}: {2}\n'.format(prefix, path, stats))
        total += stats

    out.write('{0}total: {1}\n'.format(prefix, total))
    return total


def print_stats(env_path, out=None):
    """ Print the number of entries of each named database of env_path
    """
    out = out or sys.stdout
    env = lmdb.open(env_path, readonly=True, max_dbs=LMDBResolver.MAX_DBS)
    try:
        with env.begin() as txn:
            names = [key for key, _ in txn.cursor()]

        info = env.info()
        out.write('map_size={0} last_txnid={1} readers={2}/{3}\n'.format(
            info['map_size'], info['last_txnid'], info['num_readers'], info['max_readers']))

        for name in names:
            try:
                db = env.open_db(name, create=False)
            except lmdb.Error:
                # a key of the main database, not a named database
                continue

            with env.begin(db=db) as txn:
                out.write('{0}: entries={1}\n'.format(name.decode('utf-8'), txn.stat(db)['entries']))
    finally:
        env.close()


#=================================================================
def main(args=None):
    description = """
Load path index files into an LMDB database, for the lmdb:// archive_paths:

  archive_paths: lmdb:///path/to/pathindex.lmdb?db=name
"""

    epilog = """
Some examples:

* Load or update a path index into the "primary" database
{0} load --env /data/pathindex.lmdb --db primary /data/warc-paths.txt

* Only show what would change: added, updated, unchanged and dropped entries
{0} load --dry-run --env /data/pathindex.lmdb --db primary /data/warc-paths.txt

* Recreate the "primary" database from all the .txt files of a directory
{0} load --drop --pattern '.*\\.txt' --env /data/pathindex.lmdb --db primary /data/pathindex/

* Show the number of entries of each database
{0} stats --env /data/pathindex.lmdb
""".format(os.path.basename(sys.argv[0]))

    parser = ArgumentParser(description=description,
                            epilog=epilog,
                            formatter_class=RawTextHelpFormatter)

    commands = parser.add_subparsers(dest='command')
    commands.required = True

    load_parser = commands.add_parser('load', help='load or update path index files into an LMDB database')
    load_parser.add_argument('--env', required=True, help='LMDB environment directory, created if missing')
    load_parser.add_argument('--db', required=True, help='LMDB named database')
    load_parser.add_argument('--drop', '--recreate', action='store_true',
                             help='empty the database before loading')
    load_parser.add_argument('--dry-run', action='store_true', help="show what would change, don't write")
    load_parser.add_argument('--pattern', help='regex that the names of the files of a directory must fully match')
    load_parser.add_argument('--map-size', type=int, default=DEFAULT_MAP_SIZE_GIB,
                             help='max size of the LMDB environment in GiB (default: %(default)s)')
    load_parser.add_argument('paths', nargs='+', help='path index files or directories')

    stats_parser = commands.add_parser('stats', help='show the number of entries of each database')
    stats_parser.add_argument('--env', required=True, help='LMDB environment directory')

    args = parser.parse_args(args)

    if lmdb is None:
        sys.stderr.write('error: the lmdb package is required, install it with: pip install lmdb\n')
        return 1

    try:
        if args.command == 'load':
            load(args.env, args.db, args.paths, pattern=args.pattern, drop=args.drop,
                 dry_run=args.dry_run, map_size=args.map_size * GIB)
        else:
            print_stats(args.env)

    except (IOError, ValueError, re.error, lmdb.Error) as e:
        if isinstance(e, lmdb.MapFullError):
            e = '{0}, use a bigger --map-size'.format(e)

        sys.stderr.write('error: {0}\n'.format(e))
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
