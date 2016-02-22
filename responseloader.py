from liverec import BaseRecorder
from liverec import request as remote_request

from pywb.warc.recordloader import ArcWarcRecordLoader, ArchiveLoadFailed
from pywb.utils.timeutils import timestamp_to_datetime, datetime_to_http_date
from pywb.warc.resolvingloader import ResolvingLoader

from io import BytesIO
from bottle import response

import uuid


#=============================================================================
def incr_reader(stream, header=None, size=8192):
    if header:
        yield header

    while True:
        data = stream.read(size)
        if data:
            yield data
        else:
            break


#=============================================================================
class WARCPathPrefixLoader(object):
    def __init__(self, prefix, cdx_loader):
        self.prefix = prefix

        def add_prefix(filename, cdx):
            return [self.prefix + filename]

        self.resolve_loader = ResolvingLoader([add_prefix], no_record_parse=True)
        self.cdx_loader = cdx_loader

    def __call__(self, cdx):
        if not cdx.get('filename') or cdx.get('offset') is None:
            return None

        failed_files = []
        headers, payload = self.resolve_loader.load_headers_and_payload(cdx, failed_files, self.cdx_loader)

        if headers != payload:
            headers.stream.close()

        record = payload

        for n, v in record.rec_headers.headers:
            response.headers[n] = v

        return incr_reader(record.stream)


#=============================================================================
class HeaderRecorder(BaseRecorder):
    def __init__(self, skip_list=None):
        self.buff = BytesIO()
        self.skip_list = skip_list
        self.skipped = []

    def write_response_header_line(self, line):
        if self.accept_header(line):
            self.buff.write(line)

    def get_header(self):
        return self.buff.getvalue()

    def accept_header(self, line):
        if self.skip_list and line.lower().startswith(self.skip_list):
            self.skipped.append(line)
            return False

        return True


#=============================================================================
class LiveWebLoader(object):
    SKIP_HEADERS = (b'link',
                    b'memento-datetime',
                    b'content-location',
                    b'x-archive')

    def __call__(self, cdx):
        load_url = cdx.get('load_url')
        if not load_url:
            return None

        recorder = HeaderRecorder(self.SKIP_HEADERS)

        req_headers = {}

        dt = timestamp_to_datetime(cdx['timestamp'])

        if not cdx.get('is_live'):
            req_headers['Accept-Datetime'] = datetime_to_http_date(dt)

        upstream_res = remote_request(load_url,
                                      recorder=recorder,
                                      stream=True,
                                      headers=req_headers)

        resp_headers = recorder.get_header()

        response.headers['Content-Type'] = 'application/http; msgtype=response'

        #response.headers['WARC-Type'] = 'response'
        #response.headers['WARC-Record-ID'] = self._make_warc_id()
        response.headers['WARC-Target-URI'] = cdx['url']
        response.headers['WARC-Date'] = self._make_date(dt)

        # Try to set content-length, if it is available and valid
        try:
            content_len = int(upstream_res.headers.get('content-length', 0))
            if content_len > 0:
                content_len += len(resp_headers)
                response.headers['Content-Length'] = content_len
        except:
            raise

        return incr_reader(upstream_res.raw, header=resp_headers)

    @staticmethod
    def _make_date(dt):
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def _make_warc_id(id_=None):
        if not id_:
            id_ = uuid.uuid1()
        return '<urn:uuid:{0}>'.format(id_)

