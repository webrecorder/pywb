from gevent.pool import Pool
import gevent

from concurrent import futures

import json
import time
import os

from pywb.utils.timeutils import timestamp_now
from pywb.cdx.cdxops import process_cdx
from pywb.cdx.query import CDXQuery

from heapq import merge
from collections import deque

from rezag.indexsource import FileIndexSource
from pywb.utils.wbexception import NotFoundException
import six
import glob


#=============================================================================
class BaseAggregator(object):
    def __call__(self, params):
        if params.get('closest') == 'now':
            params['closest'] = timestamp_now()

        query = CDXQuery(params)
        self._set_src_params(params)

        try:
            cdx_iter = self.load_index(query.params)
        except NotFoundException as nf:
            cdx_iter = iter([])

        cdx_iter = process_cdx(cdx_iter, query)
        return cdx_iter

    def _set_src_params(self, params):
        src_params = {}
        for param, value in six.iteritems(params):
            if not param.startswith('param.'):
                continue

            parts = param.split('.', 3)[1:]

            if len(parts) == 2:
                src = parts[0]
                name = parts[1]
            else:
                src = ''
                name = parts[0]

            if not src in src_params:
                src_params[src] = {}

            src_params[src][name] = value

        params['_all_src_params'] = src_params

    def load_child_source_list(self, name, source, params):
        return list(self.load_child_source(name, source, params))

    def load_child_source(self, name, source, params):
        try:
            _src_params = params['_all_src_params'].get(name)
            params['_src_params'] = _src_params
            cdx_iter = source.load_index(params)
        except NotFoundException as nf:
            print('Not found in ' + name)
            cdx_iter = iter([])

        def add_name(cdx):
            if cdx.get('source'):
                cdx['source'] = name + ':' + cdx['source']
            else:
                cdx['source'] = name
            return cdx

        return (add_name(cdx) for cdx in cdx_iter)

    def load_index(self, params):
        iter_list = self._load_all(params)

        #optimization: if only a single entry (or empty) just load directly
        if len(iter_list) <= 1:
            cdx_iter = iter_list[0] if iter_list else iter([])
        else:
            cdx_iter = merge(*(iter_list))

        return cdx_iter

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
                self._on_source_error(name)

        return results


#=============================================================================
class GeventTimeoutAggregator(TimeoutMixin, GeventMixin, BaseSourceListAggregator):
    pass


#=============================================================================
class ConcurrentMixin(object):
    def __init__(self, *args, **kwargs):
        super(ConcurrentMixin, self).__init__(*args, **kwargs)
        if kwargs.get('use_processes'):
            self.pool_class = futures.ThreadPoolExecutor
        else:
            self.pool_class = futures.ProcessPoolExecutor
        self.timeout = kwargs.get('timeout', 5.0)
        self.size = kwargs.get('size')

    def _load_all(self, params):
        params['_timeout'] = self.timeout

        sources = list(self._iter_sources(params))

        with self.pool_class(max_workers=self.size) as executor:
            def do_spawn(name, source):
                return executor.submit(self.load_child_source_list,
                                       name, source, params), name

            jobs = dict([do_spawn(name, source) for name, source in sources])

            res_done, res_not_done = futures.wait(jobs.keys(), timeout=self.timeout)

            results = []
            for job in res_done:
                results.append(job.result())

            for job in res_not_done:
                self._on_source_error(jobs[job])

        return results


#=============================================================================
class ThreadedTimeoutAggregator(TimeoutMixin, ConcurrentMixin, BaseSourceListAggregator):
    pass


#=============================================================================
class BaseDirectoryIndexSource(BaseAggregator):
    CDX_EXT = ('.cdx', '.cdxj')

    def __init__(self, base_prefix, base_dir=''):
        self.base_prefix = base_prefix
        self.base_dir = base_dir

    def _iter_sources(self, params):
        self._set_src_params(params)
        # see if specific params (when part of another agg)
        src_params = params.get('_src_params')
        if not src_params:
            # try default param. settings
            src_params = params.get('_all_src_params', {}).get('')

        if src_params:
            the_dir = self.base_dir.format(**src_params)
        else:
            the_dir = self.base_dir

        the_dir = os.path.join(self.base_prefix, the_dir)
        try:
            sources = list(self._load_files(the_dir))
        except Exception:
            raise NotFoundException(the_dir)

        return sources

    def _load_files(self, glob_dir):
        for the_dir in glob.iglob(glob_dir):
            for name in os.listdir(the_dir):
                filename = os.path.join(the_dir, name)

                if filename.endswith(self.CDX_EXT):
                    print('Adding ' + filename)
                    rel_path = os.path.relpath(the_dir, self.base_prefix)
                    if rel_path == '.':
                        rel_path = ''
                    yield rel_path, FileIndexSource(filename)

    def __str__(self):
        return 'file_dir'


class DirectoryIndexSource(SeqAggMixin, BaseDirectoryIndexSource):
    pass


