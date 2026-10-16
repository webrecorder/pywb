import hashlib
import io
import logging
import pickle

from pywb.utils.format import to_bool
from pywb.utils.loaders import load_py_name
from pywb.warcserver.index.aggregator import BaseDirectoryIndexSource, BaseSourceListAggregator
from pywb.warcserver.index.indexsource import FileIndexSource
from pywb.warcserver.index.zipnum import ZipNumIndexSource


logger = logging.getLogger('warcserver')


# =============================================================================
def init_index_cache(cache_config):
    """Create the index cache for the top-level ``index_cache`` config.

    - not set: a :class:`UwsgiIndexCache` with the default settings, if pywb
      runs in uWSGI and the uWSGI cache ``pywb-index`` is configured
    - ``false``: no index cache
    - a dict: the settings of the cache, with an optional ``class`` set to a
      ``module:Class`` string, a subclass of :class:`IndexCache`

    :return: the index cache, or None if it is disabled
    """
    if cache_config is False:
        return None

    explicit = cache_config is not None

    if cache_config is None or cache_config is True:
        cache_config = {}

    if not isinstance(cache_config, dict):
        raise Exception('"index_cache" config must be false or a dict')

    name = cache_config.get('class')
    cls = load_py_name(name) if name else UwsgiIndexCache

    index_cache = cls(cache_config)
    if not index_cache.enabled:
        if explicit:
            logger.warning('index_cache: {0} is not available, the index cache is disabled'.format(index_cache))
        return None

    return index_cache


# =============================================================================
class IndexCache(object):
    """Cache of the captures that the index sources of a collection return
    for a url, before they are sorted, filtered and limited.

    With ``redirect_to_exact``, a request for a url at a timestamp that isn't
    the timestamp of a capture is redirected to the closest capture, and the
    browser then requests the url again at that timestamp. Both requests read
    the same captures from the index. With this cache, the second request
    doesn't read the index again. Other requests for the same url within
    ``ttl`` seconds don't either.

    Only exact url queries to local indexes (CDX(J) files, directories of them
    and ZipNum indexes) are cached. An entry is kept for ``ttl`` seconds, so
    captures added to an index may not be found during that time.

    This is an extension point: subclasses store the entries, implementing
    :meth:`get` and :meth:`set`, and may override :meth:`can_cache`.
    """
    DEFAULT_TTL = 60

    DEFAULT_MAX_CAPTURES = 1000

    # query params not used to read the index sources, so not part of the key:
    # used by process_cdx() or to format the output, or the warcserver mode,
    # so that the lookup of the original of a revisit and the cdx api share
    # the entry. The key and end_key params, from the url, are part of it.
    IGNORED_PARAMS = frozenset(('url', 'alt_url', 'closest', 'sort', 'limit',
                                'filter', 'content_type', 'from', 'from_ts', 'to',
                                'collapseTime', 'resolveRevisits', 'reverse',
                                'fl', 'fields', 'output', 'memento_format', 'mode'))

    # first byte of an entry, for the format of the entry
    ENTRY_FORMAT = b'\x01'

    def __init__(self, config):
        self.ttl = int(config.get('ttl', self.DEFAULT_TTL))
        self.max_captures = int(config.get('max_captures', self.DEFAULT_MAX_CAPTURES))
        self.enabled = True

    def get(self, key):  # pragma: no cover
        """Return the entry for this key, as bytes, or None"""
        raise NotImplementedError()

    def set(self, key, value):  # pragma: no cover
        """Store the entry (bytes) for this key, for ``self.ttl`` seconds"""
        raise NotImplementedError()

    def can_cache(self, source):
        """Return True if the captures of this index source can be cached"""
        if isinstance(source, BaseSourceListAggregator):
            return all(self.can_cache(child) for child in source.sources.values())

        return isinstance(source, (FileIndexSource, ZipNumIndexSource, BaseDirectoryIndexSource))

    def enable_for(self, agg, name):
        """Use this cache for the aggregator of a collection, if it can be
        cached. ``name`` must be different for each aggregator.
        """
        if not self.can_cache(agg):
            logger.info('index_cache: not used for {0}, it has non-local index sources'.format(name))
            return False

        agg.index_cache = self
        agg.index_cache_name = name
        return True

    def is_cacheable_query(self, params):
        if params.get('matchType', 'exact') != 'exact':
            return False

        for name in ('showNumPages', 'showPagedIndex'):
            if to_bool(params.get(name)):
                return False

        return True

    def make_key(self, name, params):
        items = sorted((n, v) for n, v in params.items()
                       if not n.startswith('_') and n not in self.IGNORED_PARAMS)

        data = repr((name, items)).encode('utf-8')
        return hashlib.sha256(data).hexdigest()

    def load_index(self, name, load_index, params):
        """Return the captures and errors of ``load_index(params)``, from the
        cache if possible.
        """
        if not self.is_cacheable_query(params):
            return load_index(params)

        try:
            # an index source may stop reading at 'limit' captures, eg. when
            # it reads only the captures closest to 'closest'. A list with
            # fewer captures is then complete.
            max_captures = min(self.max_captures, int(params.get('limit', 100000)) - 1)
        except ValueError:
            return load_index(params)

        key = self.make_key(name, params)

        value = self.get(key)
        if value is not None:
            try:
                return iter(self.load_entry(value)), []
            except Exception:
                logger.exception('index_cache: invalid entry for {0}'.format(params.get('url')))

        cdx_iter, errs = load_index(params)

        errs = list(errs)
        if errs:
            return cdx_iter, errs

        return self._store_when_done(key, cdx_iter, max_captures), errs

    def _store_when_done(self, key, cdx_iter, max_captures):
        # store the captures if they are all read, and there are not too many
        buff = io.BytesIO()
        buff.write(self.ENTRY_FORMAT)
        count = 0

        for cdx in cdx_iter:
            if buff is not None:
                count += 1
                if count > max_captures:
                    buff = None
                else:
                    # dumped now, as process_cdx() may change the cdx
                    pickle.dump(cdx, buff, pickle.HIGHEST_PROTOCOL)

            yield cdx

        if buff is not None:
            self.set(key, buff.getvalue())

    def load_entry(self, value):
        if value[:1] != self.ENTRY_FORMAT:
            raise ValueError('unknown entry format')

        buff = io.BytesIO(value)
        buff.seek(1)

        cdx_list = []
        while buff.tell() < len(value):
            cdx_list.append(pickle.load(buff))

        return cdx_list


# =============================================================================
class UwsgiIndexCache(IndexCache):
    """Stores the entries in a uWSGI cache, shared by all uWSGI workers.

    The cache must be configured in uWSGI, with the ``cache2`` option, eg.::

        cache2 = name=pywb-index,items=20000,keysize=64,blocksize=4096,blocks=50000,bitmap=1,purge_lru=1,ignore_full=1

    It is named ``pywb-index`` by default, or the ``uwsgi_cache`` setting.
    """
    DEFAULT_CACHE_NAME = 'pywb-index'

    def __init__(self, config):
        super(UwsgiIndexCache, self).__init__(config)
        self.cache_name = config.get('uwsgi_cache', self.DEFAULT_CACHE_NAME)

        try:
            import uwsgi
        except ImportError:
            uwsgi = None

        self.uwsgi = uwsgi
        self.enabled = bool(uwsgi) and self.cache_name in self.get_cache_names(uwsgi)

    @staticmethod
    def get_cache_names(uwsgi):
        cache_opts = uwsgi.opt.get('cache2') or []
        if not isinstance(cache_opts, list):
            cache_opts = [cache_opts]

        names = set()
        for cache_opt in cache_opts:
            if isinstance(cache_opt, bytes):
                cache_opt = cache_opt.decode('utf-8')

            for setting in cache_opt.split(','):
                if setting.startswith('name='):
                    names.add(setting[5:])

        return names

    def get(self, key):
        return self.uwsgi.cache_get(key, self.cache_name)

    def set(self, key, value):
        # not stored if the cache is full or the value is too large
        self.uwsgi.cache_update(key, value, self.ttl, self.cache_name)

    def __str__(self):
        return 'uWSGI cache "{0}"'.format(self.cache_name)
