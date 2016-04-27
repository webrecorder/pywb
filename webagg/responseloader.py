from webagg.utils import MementoUtils, StreamIter, chunk_encode_iter
from webagg.utils import ParamFormatter
from webagg.indexsource import RedisIndexSource

from pywb.utils.timeutils import timestamp_to_datetime, datetime_to_timestamp
from pywb.utils.timeutils import iso_date_to_datetime, datetime_to_iso_date
from pywb.utils.timeutils import http_date_to_datetime, datetime_to_http_date

from pywb.utils.wbexception import LiveResourceException, WbException
from pywb.utils.statusandheaders import StatusAndHeaders, StatusAndHeadersParser

from pywb.warc.resolvingloader import ResolvingLoader

from six.moves.urllib.parse import urlsplit

#from io import BytesIO

import uuid
import six
import itertools
#import requests
import urllib3


#=============================================================================
class BaseLoader(object):
    def __call__(self, cdx, params):
        entry = self.load_resource(cdx, params)
        if not entry:
            return None, None

        warc_headers, other_headers, stream = entry

        out_headers = {}
        out_headers['WebAgg-Type'] = 'warc'
        out_headers['WebAgg-Source-Coll'] = cdx.get('source', '')
        out_headers['Content-Type'] = 'application/warc-record'

        if not warc_headers:
            if other_headers:
                out_headers['Link'] = other_headers.get('Link')
                out_headers['Memento-Datetime'] = other_headers.get('Memento-Datetime')
                out_headers['Content-Length'] = other_headers.get('Content-Length')

            return out_headers, StreamIter(stream)

        out_headers['Link'] = MementoUtils.make_link(
                                warc_headers.get_header('WARC-Target-URI'),
                                'original')

        memento_dt = iso_date_to_datetime(warc_headers.get_header('WARC-Date'))
        out_headers['Memento-Datetime'] = datetime_to_http_date(memento_dt)

        warc_headers_buff = warc_headers.to_bytes()

        lenset = self._set_content_len(warc_headers.get_header('Content-Length'),
                                     out_headers,
                                     len(warc_headers_buff))

        streamiter = StreamIter(stream,
                                header1=warc_headers_buff,
                                header2=other_headers)

        if not lenset:
            out_headers['Transfer-Encoding'] = 'chunked'
            streamiter = chunk_encode_iter(streamiter)

        return out_headers, streamiter

    def _set_content_len(self, content_len_str, headers, existing_len):
        # Try to set content-length, if it is available and valid
        try:
            content_len = int(content_len_str)
        except (KeyError, TypeError):
            content_len = -1

        if content_len >= 0:
            content_len += existing_len
            headers['Content-Length'] = str(content_len)
            return True

        return False

    def raise_on_self_redirect(self, params, cdx, status_code, location_url):
        """
        Check if response is a 3xx redirect to the same url
        If so, reject this capture to avoid causing redirect loop
        """
        if not status_code.startswith('3') or status_code == '304':
            return

        request_url = params['url'].lower()
        if not location_url:
            return

        location_url = location_url.lower()
        if location_url.startswith('/'):
            host = urlsplit(cdx['url']).netloc
            location_url = host + location_url

        if request_url == location_url:
            msg = 'Self Redirect {0} -> {1}'
            msg = msg.format(request_url, location_url)
            #print(msg)
            raise WbException(msg)


#=============================================================================
class PrefixResolver(object):
    def __init__(self, template):
        self.template = template

    def __call__(self, filename, cdx):
        full_path = self.template
        if hasattr(cdx, '_formatter') and cdx._formatter:
            full_path = cdx._formatter.format(full_path)

        return full_path + filename


#=============================================================================
class RedisResolver(RedisIndexSource):
    def __call__(self, filename, cdx):
        redis_key = self.redis_key_template
        if hasattr(cdx, '_formatter') and cdx._formatter:
            redis_key = cdx._formatter.format(redis_key)

        res = self.redis.hget(redis_key, filename)
        if res and six.PY3:
            res = res.decode('utf-8')

        return res


#=============================================================================
class WARCPathLoader(BaseLoader):
    def __init__(self, paths, cdx_source):
        self.paths = paths
        if isinstance(paths, six.string_types):
            self.paths = [paths]

        self.resolvers = [self._make_resolver(path) for path in self.paths]

        self.resolve_loader = ResolvingLoader(self.resolvers,
                                              no_record_parse=True)

        self.headers_parser = StatusAndHeadersParser([], verify=False)

        self.cdx_source = cdx_source

    def cdx_index_source(self, *args, **kwargs):
        cdx_iter, errs = self.cdx_source(*args, **kwargs)
        return cdx_iter

    def _make_resolver(self, path):
        if hasattr(path, '__call__'):
            return path

        if path.startswith('redis://'):
            return RedisResolver(path)

        else:
            return PrefixResolver(path)

    def load_resource(self, cdx, params):
        if cdx.get('_cached_result'):
            return cdx.get('_cached_result')

        if not cdx.get('filename') or cdx.get('offset') is None:
            return None

        cdx._formatter = ParamFormatter(params, cdx.get('source'))

        failed_files = []
        headers, payload = (self.resolve_loader.
                             load_headers_and_payload(cdx,
                                                      failed_files,
                                                      self.cdx_index_source))

        if cdx.get('status', '').startswith('3'):
            status_headers = self.headers_parser.parse(payload.stream)
            self.raise_on_self_redirect(params, cdx,
                                        status_headers.get_statuscode(),
                                        status_headers.get_header('Location'))
            http_headers_buff = status_headers.to_bytes()
        else:
            http_headers_buff = None

        warc_headers = payload.rec_headers

        if headers != payload:
            warc_headers.replace_header('WARC-Refers-To-Target-URI',
                     payload.rec_headers.get_header('WARC-Target-URI'))

            warc_headers.replace_header('WARC-Refers-To-Date',
                     payload.rec_headers.get_header('WARC-Date'))

            warc_headers.replace_header('WARC-Target-URI',
                     headers.rec_headers.get_header('WARC-Target-URI'))

            warc_headers.replace_header('WARC-Date',
                     headers.rec_headers.get_header('WARC-Date'))

            headers.stream.close()

        return (warc_headers, http_headers_buff, payload.stream)

    def __str__(self):
        return  'WARCPathLoader'


#=============================================================================
class LiveWebLoader(BaseLoader):
    SKIP_HEADERS = ('link',
                    'memento-datetime',
                    'content-location',
                    'x-archive')

    def __init__(self):
        self.num_retries = 3
        self.num_pools = 10
        self.num_conn_per_pool = 10

        self.pool = urllib3.PoolManager(num_pools=self.num_pools,
                                        maxsize=self.num_conn_per_pool)

    def load_resource(self, cdx, params):
        load_url = cdx.get('load_url')
        if not load_url:
            return None

        input_req = params['_input_req']

        req_headers = input_req.get_req_headers()

        dt = timestamp_to_datetime(cdx['timestamp'])

        if cdx.get('memento_url'):
            req_headers['Accept-Datetime'] = datetime_to_http_date(dt)

        method = input_req.get_req_method()
        data = input_req.get_req_body()

        try:
            upstream_res = self.pool.urlopen(method=method,
                                             url=load_url,
                                             body=data,
                                             headers=req_headers,
                                             redirect=False,
                                             assert_same_host=False,
                                             preload_content=False,
                                             decode_content=False,
                                             retries=self.num_retries,
                                             timeout=params.get('_timeout'))

        except Exception as e:
            raise LiveResourceException(load_url)

        memento_dt = upstream_res.headers.get('Memento-Datetime')
        if memento_dt:
            dt = http_date_to_datetime(memento_dt)
            cdx['timestamp'] = datetime_to_timestamp(dt)
        elif cdx.get('memento_url'):
        # if 'memento_url' set and no Memento-Datetime header present
        # then its an error
            return None

        agg_type = upstream_res.headers.get('WebAgg-Type')
        if agg_type == 'warc':
            cdx['source'] = upstream_res.headers.get('WebAgg-Source-Coll')
            return None, upstream_res.headers, upstream_res

        self.raise_on_self_redirect(params, cdx,
                                    str(upstream_res.status),
                                    upstream_res.headers.get('Location'))


        if upstream_res.version == 11:
            version = '1.1'
        else:
            version = '1.0'

        status = 'HTTP/{version} {status} {reason}\r\n'
        status = status.format(version=version,
                               status=upstream_res.status,
                               reason=upstream_res.reason)

        http_headers_buff = status

        orig_resp = upstream_res._original_response

        try:  #pragma: no cover
        #PY 3
            resp_headers = orig_resp.headers._headers
            for n, v in resp_headers:
                if n.lower() in self.SKIP_HEADERS:
                    continue

                http_headers_buff += n + ': ' + v + '\r\n'
        except:  #pragma: no cover
        #PY 2
            resp_headers = orig_resp.msg.headers
            for n, v in zip(orig_resp.getheaders(), resp_headers):
                if n in self.SKIP_HEADERS:
                    continue

                http_headers_buff += v

        http_headers_buff += '\r\n'
        http_headers_buff = http_headers_buff.encode('latin-1')

        try:
            fp = upstream_res._fp.fp
            if hasattr(fp, 'raw'):  #pragma: no cover
                fp = fp.raw
            remote_ip = fp._sock.getpeername()[0]
        except:  #pragma: no cover
            remote_ip = None

        warc_headers = {}

        warc_headers['WARC-Type'] = 'response'
        warc_headers['WARC-Record-ID'] = self._make_warc_id()
        warc_headers['WARC-Target-URI'] = cdx['url']
        warc_headers['WARC-Date'] = datetime_to_iso_date(dt)
        if remote_ip:
            warc_headers['WARC-IP-Address'] = remote_ip

        warc_headers['Content-Type'] = 'application/http; msgtype=response'

        self._set_content_len(upstream_res.headers.get('Content-Length', -1),
                              warc_headers,
                              len(http_headers_buff))

        warc_headers = StatusAndHeaders('WARC/1.0', warc_headers.items())
        return (warc_headers, http_headers_buff, upstream_res)

    @staticmethod
    def _make_warc_id(id_=None):
        if not id_:
            id_ = uuid.uuid1()
        return '<urn:uuid:{0}>'.format(id_)

    def __str__(self):
        return  'LiveWebLoader'

