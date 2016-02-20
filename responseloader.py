from liverec import BaseRecorder
from liverec import request as remote_request

from pywb.warc.recordloader import ArcWarcRecordLoader, ArchiveLoadFailed
from pywb.utils.timeutils import timestamp_to_datetime

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
    def __init__(self, prefix):
        self.prefix = prefix
        self.record_loader = ArcWarcRecordLoader()

    def __call__(self, cdx):
        filename = cdx.get('filename')
        offset = cdx.get('offset')
        length = cdx.get('length', -1)

        if filename is None or offset is None:
            raise Exception

        record = self.record_loader.load(self.prefix + filename,
                                         offset,
                                         length,
                                         no_record_parse=True)

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
                    b'x-archive',
                    b'set-cookie')

    def __call__(self, cdx):
        load_url = cdx.get('load_url')
        if not load_url:
            raise Exception

        recorder = HeaderRecorder(self.SKIP_HEADERS)

        upstream_res = remote_request(load_url, recorder=recorder, stream=True,
                                      headers={'Accept-Encoding': 'identity'})

        response.headers['Content-Type'] = 'application/http; msgtype=response'

        response.headers['WARC-Type'] = 'response'
        response.headers['WARC-Record-ID'] = self._make_warc_id()
        response.headers['WARC-Target-URI'] = cdx['url']
        response.headers['WARC-Date'] = self._make_date(cdx['timestamp'])

        # Try to set content-length, if it is available and valid
        try:
            content_len = int(upstream_res.headers.get('content-length', 0))
            if content_len > 0:
                content_len += len(recorder.get_header())
                response.headers['Content-Length'] = content_len
        except:
            pass

        return incr_reader(upstream_res.raw, header=recorder.get_header())

    @staticmethod
    def _make_date(ts):
        return timestamp_to_datetime(ts).strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def _make_warc_id(id_=None):
        if not id_:
            id_ = uuid.uuid1()
        return '<urn:uuid:{0}>'.format(id_)

