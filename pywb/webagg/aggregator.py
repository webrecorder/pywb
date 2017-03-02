from gevent.pool import Pool
import gevent

import json
import time
import os

from warcio.timeutils import timestamp_now

from pywb.cdx.cdxops import process_cdx
from pywb.cdx.query import CDXQuery

from heapq import merge
from collections import deque
from itertools import chain

from pywb.webagg.indexsource import FileIndexSource, RedisIndexSource
from pywb.utils.wbexception import NotFoundException, WbException

from pywb.webagg.utils import ParamFormatter, res_template

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

        def add_name(cdx, name):
            if cdx.get('source'):
                cdx['source'] = name + ':' + cdx['source']
            else:
                cdx['source'] = name
            return cdx

        if params.get('nosource') != 'true':
            cdx_iter = (add_name(cdx, name) for cdx in cdx_iter)

        return cdx_iter, err_list

    def load_index(self, params):
        res_list = self._load_all(params)

        iter_list = [res[0] for res in res_list]
        err_list = chain(*[res[1] for res in res_list])

        #optimization: if only a single entry (or empty) just load directly
        if len(iter_list) <= 1:
            cdx_iter = iter_list[0] if iter_list else iter([])
        else:
            cdx_iter = merge(*(iter_list))

        return cdx_iter, err_list

    def _on_source_error(self, name):  #pragma: no cover
        pass

    def _load_all(self, params):  #pragma: no cover
        raise NotImplemented()

    def _iter_sources(self, params):  #pragma: no cover
        raise NotImplemented()

    def get_source_list(self, params):
        srcs = self._iter_sources(params)
        result = [(name, str(value)) for name, value in srcs]
        result = {'sources': dict(result)}
        return result


#=============================================================================
class BaseSourceListAggregator(BaseAggregator):
    def __init__(self, sources, **kwargs):
        self.sources = sources

    def get_all_sources(self, params):
        return self.sources

    def _iter_sources(self, params):
        sources = self.get_all_sources(params)
        srcs_list = params.get('sources')
        if not srcs_list:
            return sources.items()

        sel_sources = tuple(srcs_list.split(','))

        return [(name, sources[name]) for name in sources.keys() if name in sel_sources]


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
    def __init__(self, *args, **kwargs):
        super(GeventMixin, self).__init__(*args, **kwargs)
        self.pool = Pool(size=kwargs.get('size'))
        self.timeout = kwargs.get('timeout', 5.0)

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
    def __init__(self, base_prefix, base_dir=''):
        self.base_prefix = base_prefix
        self.base_dir = base_dir

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
            filename = os.path.join(the_dir, name)

            if filename.endswith(FileIndexSource.CDX_EXT):
                #print('Adding ' + filename)
                rel_path = os.path.relpath(the_dir, self.base_prefix)
                if rel_path == '.':
                    full_name = name
                else:
                    full_name = rel_path + '/' + name

                yield full_name, FileIndexSource(filename)

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
class CacheDirectoryIndexSource(DirectoryIndexSource):
    def __init__(self, *args, **kwargs):
        super(CacheDirectoryIndexSource, self).__init__(*args, **kwargs)
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

        files = super(CacheDirectoryIndexSource, self)._load_files_single_dir(the_dir)
        files = list(files)
        self.cached_file_list[the_dir] = (stat, files)
        return files


#=============================================================================
class BaseRedisMultiKeyIndexSource(BaseAggregator, RedisIndexSource):
    def _iter_sources(self, params):
        redis_key_pattern = res_template(self.redis_key_template, params)

        if '*' not in redis_key_pattern:
            keys = [redis_key_pattern.encode('utf-8')]
        else:
            keys = self.scan_keys(redis_key_pattern, params)

        for key in keys:
            key = key.decode('utf-8')
            res = self._get_source_for_key(key)
            if res:
                yield key, res

    def _get_source_for_key(self, key):
        return RedisIndexSource(None, self.redis, key)

    def __str__(self):
        return 'redis'


#=============================================================================
class RedisMultiKeyIndexSource(SeqAggMixin, BaseRedisMultiKeyIndexSource):
    pass

