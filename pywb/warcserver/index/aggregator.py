from gevent.pool import Pool
import gevent

import json
import time
import os

from warcio.timeutils import timestamp_now

from heapq import merge
from collections import deque
from itertools import chain

from pywb.utils.wbexception import NotFoundException, WbException
from pywb.utils.format import ParamFormatter, res_template

from pywb.warcserver.index.indexsource import FileIndexSource, RedisIndexSource
from pywb.warcserver.index.cdxops import process_cdx
from pywb.warcserver.index.query import CDXQuery
from pywb.warcserver.index.zipnum import ZipNumIndexSource

import six
import glob


#=============================================================================
class BaseAggregator(object):
    def __call__(self, params):
        if params.get('closest') == 'now':
            params['closest'] = timestamp_now()

        content_type = params.get('content_type')
        if content_type:
            params['filter'] = '=mime:' + content_type

        query = CDXQuery(params)

        cdx_iter, errs = self.load_index(query.params)

        cdx_iter = process_cdx(cdx_iter, query)
        return cdx_iter, dict(errs)

    def load_child_source(self, name, source, params):
        try:
            params['_name'] = name
            params['_formatter'] = ParamFormatter(params, name)
            res = source.load_index(params)
            if isinstance(res, tuple):
                cdx_iter, err_list = res
            else:
                cdx_iter = res
                err_list = []
        except WbException as wbe:
            #print('Not found in ' + name)
            cdx_iter = iter([])
            err_list = [(name, repr(wbe))]

        def add_source(cdx, name):
            if not cdx.get('url'):
                return cdx

            if cdx.get('source'):
                cdx['source'] = name + ':' + cdx['source']
            else:
                cdx['source'] = name

            cdx['source-coll'] = self._get_coll(name)

            return cdx

        if params.get('nosource') != 'true':
            src_coll = params.get('param.' + name + '.src_coll')
            if src_coll:
                name += ':' + src_coll

            cdx_iter = (add_source(cdx, name) for cdx in cdx_iter)

        return cdx_iter, err_list

    def _get_coll(self, name):
        return name

    def load_index(self, params):
        res_list = self._load_all(params)

        iter_list = [res[0] for res in res_list]
        err_list = chain(*[res[1] for res in res_list])

        #optimization: if only a single entry (or empty) just load directly
        if len(iter_list) <= 1:
            cdx_iter = iter_list[0] if iter_list else iter([])
        else:
            cdx_iter = self._merge(iter_list)

        return cdx_iter, err_list

    def _merge(self, iter_list):
        return merge(*(iter_list))

    def _on_source_error(self, name):  #pragma: no cover
        pass

    def _load_all(self, params):  #pragma: no cover
        raise NotImplemented()

    def _iter_sources(self, params):  #pragma: no cover
        raise NotImplemented()

    def get_source_list(self, params):
        sources = self._iter_sources(params)
        result = [(name, str(value)) for name, value in sources]
        result = {'sources': dict(result)}
        return result


#=============================================================================
class BaseSourceListAggregator(BaseAggregator):
    def __init__(self, sources, **kwargs):
        self.sources = sources
        self.sources_key = kwargs.get('sources_key', 'sources')
        self.invert_sources = kwargs.get('invert_sources', False)

    def get_all_sources(self, params):
        return self.sources

    def _iter_sources(self, params):
        invert_sources = self.invert_sources
        sel_sources = params.get(self.sources_key)
        if sel_sources and sel_sources[0] == '!':
            invert_sources = True
            sel_sources = sel_sources[1:]

        if not sel_sources or sel_sources == '*':
            if not invert_sources:
                return six.iteritems(self.get_all_sources(params))
            else:
                return iter([])

        if not invert_sources:
            return self.yield_sources(sel_sources, params)
        else:
            return self.yield_invert_sources(sel_sources, params)

    def yield_sources(self, sel_sources, params):
        sources = self.get_all_sources(params)
        sel_sources = tuple(sel_sources.split(','))
        for name in sel_sources:
            if name in sources:
                yield (name, sources[name])

            elif ':' in name:
                name, param = name.split(':', 1)
                if name in sources:
                    params['param.' + name + '.src_coll'] = param
                    yield (name, sources[name])

    def yield_invert_sources(self, sel_sources, params):
        sources = self.get_all_sources(params)
        sel_sources = tuple([src.split(':', 1)[0]
                             for src in sel_sources.split(',')])

        for name in six.iterkeys(sources):
            if name not in sel_sources:
                yield (name, sources[name])


#=============================================================================
class SeqAggMixin(object):
    def __init__(self, *args, **kwargs):
        super(SeqAggMixin, self).__init__(*args, **kwargs)


    def _load_all(self, params):
        sources = self._iter_sources(params)
        return [self.load_child_source(name, source, params)
                for name, source in sources]


#=============================================================================
class SimpleAggregator(SeqAggMixin, BaseSourceListAggregator):
    pass


#=============================================================================
class TimeoutMixin(object):
    def __init__(self, *args, **kwargs):
        super(TimeoutMixin, self).__init__(*args, **kwargs)
        self.t_count = kwargs.get('t_count', 3)
        self.t_dura = kwargs.get('t_duration', 20)
        self.timeouts = {}

    def is_timed_out(self, name):
        timeout_deq = self.timeouts.get(name)
        if not timeout_deq:
            return False

        the_time = time.time()
        for t in list(timeout_deq):
            if (the_time - t) > self.t_dura:
                timeout_deq.popleft()

        if len(timeout_deq) >= self.t_count:
            print('Skipping {0}, {1} timeouts in {2} seconds'.
                  format(name, self.t_count, self.t_dura))
            return True

        return False

    def _iter_sources(self, params):
        sources = super(TimeoutMixin, self)._iter_sources(params)
        for name, source in sources:
            if not self.is_timed_out(name):
                yield name, source

    def _on_source_error(self, name):
        the_time = time.time()
        if name not in self.timeouts:
            self.timeouts[name] = deque()

        self.timeouts[name].append(the_time)
        print(name + ' timed out!')


#=============================================================================
class GeventMixin(object):
    DEFAULT_TIMEOUT = 5.0

    def __init__(self, *args, **kwargs):
        super(GeventMixin, self).__init__(*args, **kwargs)
        self.pool = Pool(size=kwargs.get('size'))
        self.timeout = kwargs.get('timeout') or self.DEFAULT_TIMEOUT

    def _load_all(self, params):
        params['_timeout'] = self.timeout

        sources = list(self._iter_sources(params))

        def do_spawn(name, source):
            return self.pool.spawn(self.load_child_source, name, source, params)

        jobs = [do_spawn(name, source) for name, source in sources]

        gevent.joinall(jobs, timeout=self.timeout)

        results = []
        for (name, source), job in zip(sources, jobs):
            if job.value is not None:
                results.append(job.value)
            else:
                results.append((iter([]), [(name, 'timeout')]))
                self._on_source_error(name)

        return results


#=============================================================================
class GeventTimeoutAggregator(TimeoutMixin, GeventMixin, BaseSourceListAggregator):
    pass


#=============================================================================
class BaseDirectoryIndexSource(BaseAggregator):
    INDEX_SOURCES = [
                     (FileIndexSource.CDX_EXT, FileIndexSource),
                     (ZipNumIndexSource.IDX_EXT, ZipNumIndexSource)
                    ]

    def __init__(self, base_prefix, base_dir='', name='', config=None):
        self.base_prefix = base_prefix
        self.base_dir = base_dir
        self.name = name
        self.config = config

    def _iter_sources(self, params):
        the_dir = res_template(self.base_dir, params)
        the_dir = os.path.join(self.base_prefix, the_dir)
        try:
            sources = list(self._load_files(the_dir))
        except Exception:
            raise NotFoundException(the_dir)

        return sources

    def _load_files(self, glob_dir):
        for the_dir in glob.iglob(glob_dir):
            for result in self._load_files_single_dir(the_dir):
                yield result

    def _load_files_single_dir(self, the_dir):
        for name in os.listdir(the_dir):
            for ext, cls in self.INDEX_SOURCES:
                if not name.endswith(ext):
                    continue

                filename = os.path.join(the_dir, name)

                 #print('Adding ' + filename)
                rel_path = os.path.relpath(the_dir, self.base_prefix)
                if rel_path == '.':
                    full_name = name
                else:
                    full_name = os.path.join(rel_path, name)

                if self.name:
                    full_name = self.name + ':' + full_name

                index_src = cls(filename, self.config)

                yield full_name, index_src

    def _get_coll(self, name):
        return name.split(os.path.sep, 1)[0]

    def __repr__(self):
        return '{0}(file://{1})'.format(self.__class__.__name__,
                                        os.path.join(self.base_prefix, self.base_dir))

    def __str__(self):
        return 'file_dir'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.base_prefix == other.base_prefix and
                self.base_dir == other.base_dir)

    @classmethod
    def init_from_string(cls, value):
        if os.path.sep != '/':
            value = value.replace('/', os.path.sep)
        if '://' not in value and os.path.isdir(value):
            return cls(value)

    @classmethod
    def init_from_config(cls, config):
        if config['type'] != 'file':
            return

        return cls.init_from_string(config['path'])


#=============================================================================
class DirectoryIndexSource(SeqAggMixin, BaseDirectoryIndexSource):
    pass


#=============================================================================
class CacheDirectoryMixin(object):
    def __init__(self, *args, **kwargs):
        super(CacheDirectoryMixin, self).__init__(*args, **kwargs)
        self.cached_file_list = {}

    def _load_files_single_dir(self, the_dir):
        try:
            stat = os.stat(the_dir)
        except Exception as e:
            stat = 0

        result = self.cached_file_list.get(the_dir)

        if result:
            last_stat, files = result
            if stat and last_stat == stat:
                print('Dir {0} unchanged'.format(the_dir))
                return files

        files = super(CacheDirectoryMixin, self)._load_files_single_dir(the_dir)
        files = list(files)
        self.cached_file_list[the_dir] = (stat, files)
        return files


#=============================================================================
class CacheDirectoryIndexSource(CacheDirectoryMixin, DirectoryIndexSource):
    pass


#=============================================================================
class BaseRedisMultiKeyIndexSource(BaseAggregator, RedisIndexSource):
    def _iter_sources(self, params):
        redis_key_pattern = res_template(self.redis_key_template, params)

        if '*' not in redis_key_pattern:
            keys = [redis_key_pattern]
        else:
            keys = self.scan_keys(redis_key_pattern, params)

        for key in keys:
            res = self._get_source_for_key(key)
            if res:
                yield key, res

    def _get_source_for_key(self, key):
        return RedisIndexSource(None, self.redis, key)

    def __str__(self):
        return 'redis-multikey'


#=============================================================================
class RedisMultiKeyIndexSource(SeqAggMixin, BaseRedisMultiKeyIndexSource):
    pass

