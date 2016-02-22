from gevent.pool import Pool
import gevent
import json
import time

from heapq import merge
from collections import deque

from indexsource import BaseIndexSource
from pywb.utils.wbexception import NotFoundException


#=============================================================================
class BaseAggIndexSource(BaseIndexSource):
    def __init__(self, sources):
        self.sources = sources

    def do_query(self, name, source, params):
        try:
            cdx_iter = source.load_index(params)
        except NotFoundException as nf:
            print('Not found in ' + name)
            cdx_iter = iter([])

        def add_name(cdx_iter):
            for cdx in cdx_iter:
                cdx['source_name'] = name
                yield cdx

        return add_name(cdx_iter)

    def load_index(self, params):
        iter_list = self._load_all(params)

        cdx_iter = merge(*(iter_list))

        return cdx_iter


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
        for name in sources.keys():
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
        super(GeventAggIndexSource, self).__init__(sources)
        self.pool = Pool(size=size)
        self.timeout = timeout

    def get_valid_sources(self, sources):
        return sources.keys()

    def track_source_error(self, name):
        pass

    def _load_all(self, params):
        def do_spawn(n):
            return self.pool.spawn(self.do_query, n, self.sources[n], params)

        jobs = [do_spawn(src) for src in self.get_valid_sources(self.sources)]

        gevent.joinall(jobs, timeout=self.timeout)

        res = []
        for name, job in zip(self.sources.keys(), jobs):
            if job.value:
                res.append(job.value)
            else:
                self.track_source_error(name)

        return res


#=============================================================================
class AggIndexSource(TimingOutMixin, GeventAggIndexSource):
    pass


#=============================================================================
class SimpleAggIndexSource(BaseAggIndexSource):
    def _load_all(self, params):
        return list(map(lambda n: self.do_query(n, self.sources[n], params),
                        self.sources))


#=============================================================================
class ResourceLoadAgg(object):
    def __init__(self, load_index, load_resource):
        self.load_index = load_index
        self.load_resource = load_resource

    def __call__(self, params):
        cdx_iter = self.load_index(params)
        for cdx in cdx_iter:
            for loader in self.load_resource:
                try:
                    resp = loader(cdx)
                    if resp:
                        return resp
                except Exception:
                    pass

                raise Exception('Not Found')


