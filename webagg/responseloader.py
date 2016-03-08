from webagg.liverec import BaseRecorder
from webagg.liverec import request as remote_request

from webagg.utils import MementoUtils

from pywb.utils.timeutils import timestamp_to_datetime, datetime_to_timestamp
from pywb.utils.timeutils import iso_date_to_datetime, datetime_to_iso_date
from pywb.utils.timeutils import http_date_to_datetime, datetime_to_http_date

from pywb.utils.wbexception import LiveResourceException
from pywb.utils.statusandheaders import StatusAndHeaders

from pywb.warc.resolvingloader import ResolvingLoader


from io import BytesIO

import uuid
import six
import itertools


#=============================================================================
class StreamIter(six.Iterator):
    def __init__(self, stream, header1=None, header2=None, size=8192):
        self.stream = stream
        self.header1 = header1
        self.header2 = header2
        self.size = size

    def __iter__(self):
        return self

    def __next__(self):
        if self.header1:
            header = self.header1
            self.header1 = None
            return header
        elif self.header2:
            header = self.header2
            self.header2 = None
            return header

        data = self.stream.read(self.size)
        if data:
            return data

        self.close()
        raise StopIteration

    def close(self):
        if not self.stream:
            return

        try:
            self.stream.close()
            self.stream = None
        except Exception:
            pass


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

                #for n, v in other_headers.items():
                #    out_headers[n] = v

            return out_headers, StreamIter(stream)

        out_headers['Link'] = MementoUtils.make_link(
                                warc_headers.get_header('WARC-Target-URI'),
                                'original')

        memento_dt = iso_date_to_datetime(warc_headers.get_header('WARC-Date'))
        out_headers['Memento-Datetime'] = datetime_to_http_date(memento_dt)

        warc_headers_buff = warc_headers.to_bytes()

        self._set_content_len(warc_headers.get_header('Content-Length'),
                              out_headers,
                              len(warc_headers_buff))

        return out_headers, StreamIter(stream,
                                       header1=warc_headers_buff,
                                       header2=other_headers)

    def _set_content_len(self, content_len_str, headers, existing_len):
        # Try to set content-length, if it is available and valid
        try:
            content_len = int(content_len_str)
        except (KeyError, TypeError):
            content_len = -1

        if content_len >= 0:
            content_len += existing_len
            headers['Content-Length'] = str(content_len)


#=============================================================================
class WARCPathLoader(BaseLoader):
    def __init__(self, paths, cdx_source):
        self.paths = paths
        if isinstance(paths, str):
            self.paths = [paths]

        self.path_checks = list(self.warc_paths())

        self.resolve_loader = ResolvingLoader(self.path_checks,
                                              no_record_parse=True)
        self.cdx_source = cdx_source

    def cdx_index_source(self, *args, **kwargs):
        cdx_iter, errs = self.cdx_source(*args, **kwargs)
        return cdx_iter

    def warc_paths(self):
        for path in self.paths:
            def check(filename, cdx):
                try:
                    if hasattr(cdx, '_formatter') and cdx._formatter:
                        full_path = cdx._formatter.format(path)
                    else:
                        full_path = path
                    full_path += filename
                    return full_path
                except KeyError:
                    return None

            yield check

    def load_resource(self, cdx, params):
        if cdx.get('_cached_result'):
            return cdx.get('_cached_result')

        if not cdx.get('filename') or cdx.get('offset') is None:
            return None

        cdx._formatter = params.get('_formatter')
        failed_files = []
        headers, payload = (self.resolve_loader.
                             load_headers_and_payload(cdx,
                                                      failed_files,
                                                      self.cdx_index_source))
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

        return (warc_headers, None, payload.stream)

    def __str__(self):
        return  'WARCPathLoader'


#=============================================================================
class LiveWebLoader(BaseLoader):
    SKIP_HEADERS = (b'link',
                    b'memento-datetime',
                    b'content-location',
                    b'x-archive')

    def load_resource(self, cdx, params):
        load_url = cdx.get('load_url')
        if not load_url:
            return None

        recorder = HeaderRecorder(self.SKIP_HEADERS)

        input_req = params['_input_req']

        req_headers = input_req.get_req_headers()

        dt = timestamp_to_datetime(cdx['timestamp'])

        if cdx.get('memento_url'):
            req_headers['Accept-Datetime'] = datetime_to_http_date(dt)

        # if different url, ensure origin is not set
        # may need to add other headers
        if load_url != cdx['url']:
            if 'Origin' in req_headers:
                splits = urlsplit(load_url)
                req_headers['Origin'] = splits.scheme + '://' + splits.netloc

        method = input_req.get_req_method()
        data = input_req.get_req_body()

        try:
            upstream_res = remote_request(url=load_url,
                                          method=method,
                                          recorder=recorder,
                                          stream=True,
                                          allow_redirects=False,
                                          headers=req_headers,
                                          data=data,
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
            return None, upstream_res.headers, upstream_res.raw

        http_headers_buff = recorder.get_headers_buff()

        warc_headers = {}

        warc_headers['WARC-Type'] = 'response'
        warc_headers['WARC-Record-ID'] = self._make_warc_id()
        warc_headers['WARC-Target-URI'] = cdx['url']
        warc_headers['WARC-Date'] = datetime_to_iso_date(dt)
        if recorder.target_ip:
            warc_headers['WARC-IP-Address'] = recorder.target_ip

        warc_headers['Content-Type'] = 'application/http; msgtype=response'

        self._set_content_len(upstream_res.headers.get('Content-Length', -1),
                              warc_headers,
                              len(http_headers_buff))

        warc_headers = StatusAndHeaders('WARC/1.0', warc_headers.items())
        return (warc_headers, http_headers_buff, upstream_res.raw)

    @staticmethod
    def _make_warc_id(id_=None):
        if not id_:
            id_ = uuid.uuid1()
        return '<urn:uuid:{0}>'.format(id_)

    def __str__(self):
        return  'LiveWebLoader'


#=============================================================================
class HeaderRecorder(BaseRecorder):
    def __init__(self, skip_list=None):
        self.buff = BytesIO()
        self.skip_list = skip_list
        self.skipped = []
        self.target_ip = None

    def write_response_header_line(self, line):
        if self.accept_header(line):
            self.buff.write(line)

    def get_headers_buff(self):
        return self.buff.getvalue()

    def accept_header(self, line):
        if self.skip_list and line.lower().startswith(self.skip_list):
            self.skipped.append(line)
            return False

        return True

    def finish_request(self, socket):
        ip = socket.getpeername()
        if ip:
            self.target_ip = ip[0]


