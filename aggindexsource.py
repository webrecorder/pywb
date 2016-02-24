from gevent.pool import Pool
import gevent
import json
import time
import os

from heapq import merge
from collections import deque

from indexsource import BaseIndexSource, FileIndexSource
from pywb.utils.wbexception import NotFoundException


#=============================================================================
class BaseAggIndexSource(BaseIndexSource):
    def do_query(self, name, source, params):
        try:
            cdx_iter = source.load_index(dict(params))
        except NotFoundException as nf:
            print('Not found in ' + name)
            cdx_iter = iter([])

        def add_name(cdx_iter):
            for cdx in cdx_iter:
                cdx['source'] = name
                yield cdx

        return add_name(cdx_iter)

    def load_index(self, params):
        iter_list = self._load_all(params)

        cdx_iter = merge(*(iter_list))

        return cdx_iter

    def _load_all(self):
        raise NotImplemented()


#=============================================================================
class TimingOutMixin(object):
    def __init__(self, *args, **kwargs):
        super(TimingOutMixin, self).__init__(*args, **kwargs)
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

    def get_valid_sources(self, sources):
        for name in sources:
            if not self.is_timed_out(name):
                yield name

    def track_source_error(self, name):
        the_time = time.time()
        if name not in self.timeouts:
            self.timeouts[name] = deque()

        self.timeouts[name].append(the_time)
        print(name + ' timed out!')


#=============================================================================
class GeventAggIndexSource(BaseAggIndexSource):
    def __init__(self, sources, timeout=5.0, size=None):
        self.sources = sources
        self.pool = Pool(size=size)
        self.timeout = timeout

    def get_sources(self, params):
        srcs_list = params.get('sources')
        if not srcs_list:
            return self.sources

        sel_sources = tuple(srcs_list.split(','))

        return [src for src in self.sources if src in sel_sources]

    def get_valid_sources(self, sources):
        return sources.keys()

    def track_source_error(self, name):
        pass

    def _load_all(self, params):
        params['_timeout'] = self.timeout

        def do_spawn(n):
            return self.pool.spawn(self.do_query, n, self.sources[n], params)

        sources = self.get_sources(params)
        jobs = [do_spawn(src) for src in self.get_valid_sources(sources)]

        gevent.joinall(jobs, timeout=self.timeout)

        res = []
        for name, job in zip(sources, jobs):
            if job.value:
                res.append(job.value)
            else:
                self.track_source_error(name)

        return res


#=============================================================================
class AggIndexSource(TimingOutMixin, GeventAggIndexSource):
    pass


#=============================================================================
class DirAggIndexSource(BaseAggIndexSource):
    CDX_EXT = ('.cdx', '.cdxj')

    def __init__(self, base_dir):
        self.index_template = base_dir

    def _init_files(self, the_dir):
        sources = {}
        for name in os.listdir(the_dir):
            filename = os.path.join(the_dir, name)

            if filename.endswith(self.CDX_EXT):
                print('Adding ' + filename)
                sources[name] = FileIndexSource(filename)

        return sources

    def _load_all(self, params):
        the_dir = self.get_index(params)

        try:
            sources = self._init_files(the_dir)
        except Exception:
            raise NotFoundException(the_dir)

        return list([self.do_query(src, sources[src], params)
                     for src in sources.keys()])
