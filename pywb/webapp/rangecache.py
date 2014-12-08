from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.loaders import LimitReader
from pywb.framework.cache import create_cache

from tempfile import NamedTemporaryFile, mkdtemp

import yaml
import os
import re

import atexit


#=================================================================
class RangeCache(object):
    YOUTUBE_RX = re.compile('.*.googlevideo.com/videoplayback')
    YT_EXTRACT_RX = re.compile('&range=([^&]+)')

    DEFAULT_BUFF = 16384*4

    @staticmethod
    def match_yt(url):
        if not RangeCache.YOUTUBE_RX.match(url):
            return None

        range_h_res = []

        def repl_range(matcher):
            range_h_res.append(matcher.group(1))
            return ''

        new_url = RangeCache.YT_EXTRACT_RX.sub(repl_range, url)
        if range_h_res:
            return range_h_res[0], new_url
        else:
            return None, url

    def __init__(self):
        self.cache = create_cache()
        self.temp_dir = None
        atexit.register(self.cleanup)

    def cleanup(self):
        if self.temp_dir:
            import shutil
            print('Removing: ' + self.temp_dir)
            shutil.rmtree(self.temp_dir, True)

    def is_ranged(self, wbrequest):
        url = wbrequest.wb_url.url
        range_h = None
        use_206 = False

        result = self.match_yt(url)
        if result:
            range_h, url = result

            if wbrequest.env.get('HTTP_X_IGNORE_RANGE_ARG'):
                wbrequest.wb_url.url = url
                return None

        # check for standard range header
        if not range_h:
            range_h = wbrequest.env.get('HTTP_RANGE')
            if not range_h:
                return None

            use_206 = True

        # force bounded range
        range_h = range_h.split('=')[-1]
        range_h = range_h.rstrip()
        parts = range_h.split('-', 1)
        start = int(parts[0])
        if len(parts) == 2 and parts[1]:
            end = int(parts[1])
        else:
            #end = start + self.DEFAULT_BUFF - 1
            end = ''

        return url, start, end, use_206

    def __call__(self, wbrequest, digest, wbresponse_func):
        result = self.is_ranged(wbrequest)
        if not result:
            return None, None

        return self.handle_range(wbrequest, digest, wbresponse_func,
                                 *result)

    def handle_range(self, wbrequest, digest, wbresponse_func,
                     url, start, end, use_206):

        key = digest
        if not key in self.cache:
            wbrequest.custom_params['noredir'] = True
            response = wbresponse_func()

            # only cache 200 responses
            if not response.status_headers.get_statuscode().startswith('200'):
                print('NON 200 RESP')
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
            with open(spec['name']) as fh:
                fh.seek(start)
                fh = LimitReader.wrap_stream(fh, maxlen)
                while True:
                    buf = fh.read()
                    if not buf:
                        break

                    yield buf

        if use_206:
            content_range = 'bytes {0}-{1}/{2}'.format(start,
                                                       start + maxlen - 1,
                                                       filelen)

            status_headers = StatusAndHeaders('206 Partial Content', spec['headers'])
            status_headers.replace_header('Content-Range', content_range)
            status_headers.replace_header('Accept-Ranges', 'bytes')
        else:
            status_headers = StatusAndHeaders('200 OK', spec['headers'])

        status_headers.replace_header('Content-Length', str(maxlen))

        return status_headers, read_range()


#=================================================================
range_cache = RangeCache()
