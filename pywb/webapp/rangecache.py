from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.utils.loaders import LimitReader
from pywb.framework.cache import create_cache

from tempfile import NamedTemporaryFile

import yaml
import os
import re


#=================================================================
class RangeCache(object):
    YOUTUBE_RX = re.compile('.*.googlevideo.com/videoplayback')
    YT_EXTRACT_RX = re.compile('&range=([^&]+)')

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

    def is_ranged(self, wbrequest):
        url = wbrequest.wb_url.url
        range_h = None
        use_206 = False

        result = self.match_yt(url)
        if result:
            range_h, url = result

        # check for standard range header
        if not range_h:
            range_h = wbrequest.env.get('HTTP_RANGE')
            if not range_h:
                return None

            use_206 = True

        return url, range_h, use_206

    def __call__(self, wbrequest, digest, wbresponse_func):
        result = self.is_ranged(wbrequest)
        if not result:
            return None, None

        return self.handle_range(wbrequest, digest, wbresponse_func,
                                 *result)

    def handle_range(self, wbrequest, digest, wbresponse_func,
                     url, range_h, use_206):

        range_h = range_h.split('=')[-1]
        key = digest
        if not key in self.cache:
            response = wbresponse_func()
            if not response:
                return None, None

            with NamedTemporaryFile(delete=False) as fh:
                for obj in response.body:
                    fh.write(obj)

                name = fh.name

            spec = dict(name=fh.name,
                        headers=response.status_headers.headers)

            self.cache[key] = yaml.dump(spec)
        else:
            spec = yaml.load(self.cache[key])
            if not spec:
                return None, None

            spec['headers'] = [tuple(x) for x in spec['headers']]

        filelen = os.path.getsize(spec['name'])

        range_h = range_h.rstrip()

        if range_h == '0-':
            range_h = '0-120000'

        parts = range_h.rstrip().split('-')
        start = parts[0]
        #start = start.split('=')[1]
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
                    if not buf:
                        break

                    yield buf

        if use_206:
            content_range = 'bytes {0}-{1}/{2}'.format(start,
                                                       start + maxlen - 1,
                                                       filelen)

            status_headers = StatusAndHeaders('206 Partial Content', spec['headers'])
            status_headers.replace_header('Content-Range', content_range)
        else:
            status_headers = StatusAndHeaders('200 OK', spec['headers'])

            #status_headers.headers.append(('Accept-Ranges', 'bytes'))
            #status_headers.headers.append(('Access-Control-Allow-Credentials', 'true'))
            #status_headers.headers.append(('Access-Control-Allow-Origin', 'http://localhost:8080'))
            #status_headers.headers.append(('Timing-Allow-Origin', 'http://localhost:8080'))

        status_headers.replace_header('Content-Length', str(maxlen))
        return status_headers, read_range()


#=================================================================
range_cache = RangeCache()
