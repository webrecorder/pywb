from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.loaders import LimitReader
from pywb.framework.cache import create_cache

from tempfile import NamedTemporaryFile, mkdtemp

import yaml
import os
from shutil import rmtree

import atexit


#=================================================================
class RangeCache(object):
    def __init__(self):
        self.cache = create_cache()
        self.temp_dir = None
        atexit.register(self.cleanup)

    def cleanup(self):
        if self.temp_dir:  # pragma: no cover
            print('Removing: ' + self.temp_dir)
            rmtree(self.temp_dir, True)
            self.temp_dir = None

    def handle_range(self, wbrequest, key, wbresponse_func,
                     url, start, end, use_206):
        # key must be set
        assert(key)
        if key not in self.cache:
            wbrequest.custom_params['noredir'] = True
            response = wbresponse_func()

            # only cache 200 responses
            if not response.status_headers.get_statuscode().startswith('200'):
                return response.status_headers, response.body

            if not self.temp_dir:
                self.temp_dir = mkdtemp(prefix='_pywbcache')
            else:
                pass
                #self._check_dir_size(self.temp_dir)

            with NamedTemporaryFile(delete=False, dir=self.temp_dir) as fh:
                for obj in response.body:
                    fh.write(obj)

                name = fh.name

            spec = dict(name=fh.name,
                        headers=response.status_headers.headers)

            self.cache[key] = yaml.dump(spec)
        else:
            spec = yaml.load(self.cache[key])

            spec['headers'] = [tuple(x) for x in spec['headers']]

        filelen = os.path.getsize(spec['name'])

        maxlen = filelen - start

        if end:
            maxlen = min(maxlen, end - start + 1)

        def read_range():
            with open(spec['name'], 'rb') as fh:
                fh.seek(start)
                fh = LimitReader.wrap_stream(fh, maxlen)
                while True:
                    buf = fh.read()
                    if not buf:
                        break

                    yield buf

        status_headers = StatusAndHeaders('200 OK', spec['headers'])

        if use_206:
            StatusAndHeaders.add_range(status_headers, start,
                                       maxlen,
                                       filelen)

        status_headers.replace_header('Content-Length', str(maxlen))

        return status_headers, read_range()


#=================================================================
range_cache = RangeCache()
