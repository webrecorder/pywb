from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.loaders import LimitReader
from pywb.framework.cache import create_cache

from tempfile import NamedTemporaryFile

import hashlib
import yaml
import os


#=================================================================
class RangeCache(object):
    def __init__(self):
        self.cache = create_cache()
        print(type(self.cache))

    def __call__(self, wbrequest, cdx, wbresponse_func):
        range_h = wbrequest.env.get('HTTP_RANGE')
        if not range_h:
            return None, None

        key = cdx.get('digest')
        if not key:
            hash_ = hashlib.md5()
            hash_.update(cdx['urlkey'])
            hash_.update(cdx['timestamp'])
            key = hash_.hexdigest()

        print('KEY: ', key)
        print('CACHE: ', str(self.cache))

        if not key in self.cache:
            print('MISS')
            response = wbresponse_func()

            with NamedTemporaryFile(delete=False) as fh:
                for obj in response.body:
                    fh.write(obj)

                name = fh.name

            spec = dict(name=fh.name,
                        headers=response.status_headers.headers)

            print('SET CACHE: ' + key)
            self.cache[key] = yaml.dump(spec)
        else:
            print('HIT')
            spec = yaml.load(self.cache[key])
            spec['headers'] = [tuple(x) for x in spec['headers']]

        print(spec['headers'])
        print('TEMP FILE: ' + spec['name'])
        filelen = os.path.getsize(spec['name'])

        range_h = range_h.rstrip()

        if range_h == 'bytes=0-':
            print('FIX RANGE')
            range_h = 'bytes=0-120000'

        parts = range_h.rstrip().split('-')
        start = parts[0]
        start = start.split('=')[1]
        start = int(start)

        maxlen = filelen - start

        if len(parts) == 2 and parts[1]:
            maxlen = min(maxlen, int(parts[1]) - start + 1)

        def read_range():
            with open(spec['name']) as fh:
                fh.seek(start)
                fh = LimitReader.wrap_stream(fh, maxlen)
                while True:
                    buf = fh.read()
                    print('READ: ', len(buf))
                    if not buf:
                        break

                    yield buf


        content_range = 'bytes {0}-{1}/{2}'.format(start,
                                                   start + maxlen - 1,
                                                   filelen)

        print('CONTENT_RANGE: ', content_range)
        status_headers = StatusAndHeaders('206 Partial Content', spec['headers'])
        status_headers.replace_header('Content-Range', content_range)
        status_headers.replace_header('Content-Length', str(maxlen))
        return status_headers, read_range()


#=================================================================
range_cache = RangeCache()
