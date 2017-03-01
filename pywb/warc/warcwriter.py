import tempfile
import uuid
import base64
import hashlib
import datetime
import zlib
import six

from socket import gethostname
from io import BytesIO

from pywb.utils.loaders import to_native_str
from pywb.utils.timeutils import datetime_to_iso_date

from pywb.utils.statusandheaders import StatusAndHeadersParser, StatusAndHeaders

from pywb.warc.recordloader import ArcWarcRecord
from pywb.warc.recordloader import ArcWarcRecordLoader


# ============================================================================
class BaseWARCWriter(object):
    BUFF_SIZE = 16384

    WARC_RECORDS = {'warcinfo': 'application/warc-fields',
         'response': 'application/http; msgtype=response',
         'revisit': 'application/http; msgtype=response',
         'request': 'application/http; msgtype=request',
         'metadata': 'application/warc-fields',
        }

    REVISIT_PROFILE = 'http://netpreserve.org/warc/1.0/revisit/uri-agnostic-identical-payload-digest'

    WARC_VERSION = 'WARC/1.0'

    def __init__(self, gzip=True, header_filter=None, *args, **kwargs):
        self.gzip = gzip
        self.header_filter = header_filter
        self.hostname = gethostname()

        self.parser = StatusAndHeadersParser([], verify=False)
        self.warc_version = kwargs.get('warc_version', self.WARC_VERSION)

    @classmethod
    def _iter_stream(cls, stream):
        while True:
            buf = stream.read(cls.BUFF_SIZE)
            if not buf:
                return

            yield buf

    def ensure_digest(self, record):
        block_digest = record.rec_headers.get_header('WARC-Block-Digest')
        payload_digest = record.rec_headers.get_header('WARC-Payload-Digest')
        if block_digest and payload_digest:
            return

        block_digester = self._create_digester()
        payload_digester = self._create_digester()

        pos = record.stream.tell()

        if record.status_headers and hasattr(record.status_headers, 'headers_buff'):
            block_digester.update(record.status_headers.headers_buff)

        for buf in self._iter_stream(record.stream):
            block_digester.update(buf)
            payload_digester.update(buf)

        record.stream.seek(pos)
        record.rec_headers.add_header('WARC-Block-Digest', str(block_digester))
        record.rec_headers.add_header('WARC-Payload-Digest', str(payload_digester))

    def _create_digester(self):
        return Digester('sha1')

    def _set_header_buff(self, record):
        exclude_list = None
        if self.header_filter:
            exclude_list = self.header_filter(record)
        buff = record.status_headers.to_bytes(exclude_list)
        record.status_headers.headers_buff = buff

    def create_warcinfo_record(self, filename, info):
        warc_headers = StatusAndHeaders(self.warc_version, [])
        warc_headers.add_header('WARC-Type', 'warcinfo')
        warc_headers.add_header('WARC-Record-ID', self._make_warc_id())
        if filename:
            warc_headers.add_header('WARC-Filename', filename)
        warc_headers.add_header('WARC-Date', self._make_warc_date())

        warcinfo = BytesIO()
        for n, v in six.iteritems(info):
            self._header(warcinfo, n, v)

        warcinfo.seek(0)

        record = ArcWarcRecord('warc', 'warcinfo', warc_headers, warcinfo,
                               None, '', len(warcinfo.getvalue()))

        return record

    def copy_warc_record(self, payload):
        len_ = payload.tell()
        payload.seek(0)

        warc_headers = self.parser.parse(payload)

        record_type = warc_headers.get_header('WARC-Type', 'response')

        return self._fill_record(record_type, warc_headers, None, payload, '', len_)

    def create_warc_record(self, uri, record_type, payload,
                           length=None,
                           warc_content_type='',
                           warc_headers_dict={},
                           status_headers=None):

        if length is None:
            length = payload.tell()
            payload.seek(0)

        warc_headers = StatusAndHeaders(self.warc_version, list(warc_headers_dict.items()))
        warc_headers.replace_header('WARC-Type', record_type)
        if not warc_headers.get_header('WARC-Record-ID'):
            warc_headers.add_header('WARC-Record-ID', self._make_warc_id())

        if uri:
            warc_headers.replace_header('WARC-Target-URI', uri)

        if not warc_headers.get_header('WARC-Date'):
            warc_headers.add_header('WARC-Date', self._make_warc_date())

        return self._fill_record(record_type, warc_headers, status_headers,
                                 payload, warc_content_type, length)

    def _fill_record(self, record_type, warc_headers, status_headers, payload, warc_content_type, len_):
        has_http_headers = (record_type in ('request', 'response', 'revisit'))

        if not status_headers and has_http_headers:
            status_headers = self.parser.parse(payload)

        record = ArcWarcRecord('warc', record_type, warc_headers, payload,
                               status_headers, warc_content_type, len_)

        self.ensure_digest(record)

        if has_http_headers:
            self._set_header_buff(record)

        return record

    def _write_warc_record(self, out, record, adjust_cl=True):
        if self.gzip:
            out = GzippingWrapper(out)

        # compute Content-Type
        content_type = record.rec_headers.get_header('Content-Type')

        if not content_type:
            content_type = record.content_type

            if not content_type:
                content_type = self.WARC_RECORDS.get(record.rec_headers.get_header('WARC-Type'))

            if content_type:
                record.rec_headers.replace_header('Content-Type', content_type)
                #self._header(out, 'Content-Type', content_type)

        if record.rec_headers.get_header('WARC-Type') == 'revisit':
            http_headers_only = True
        else:
            http_headers_only = False

        # compute Content-Length
        if record.length or record.status_headers:
            actual_len = 0
            if record.status_headers:
                actual_len = len(record.status_headers.headers_buff)

            if not http_headers_only:
                if adjust_cl:
                    diff = record.stream.tell() - actual_len
                else:
                    diff = 0

                actual_len = record.length - diff

            record.rec_headers.replace_header('Content-Length', str(actual_len))
            #self._header(out, 'Content-Length', str(actual_len))

            # add empty line
            #self._line(out, b'')

            # write record headers
            out.write(record.rec_headers.to_bytes())

            # write headers buffer, if any
            if record.status_headers:
                out.write(record.status_headers.headers_buff)

            if not http_headers_only:
                for buf in self._iter_stream(record.stream):
                    out.write(buf)
                #out.write(record.stream.read())

            # add two lines
            self._line(out, b'\r\n')
        else:
            # add three lines (1 for end of header, 2 for end of record)
            self._line(out, b'Content-Length: 0\r\n\r\n')

        out.flush()

    def _header(self, out, name, value):
        if not value:
            return

        self._line(out, (name + ': ' + str(value)).encode('latin-1'))

    def _line(self, out, line):
        out.write(line + b'\r\n')

    @classmethod
    def _make_warc_id(cls, id_=None):
        if not id_:
            id_ = uuid.uuid1()
        return '<urn:uuid:{0}>'.format(id_)

    @classmethod
    def _make_warc_date(cls):
        return datetime_to_iso_date(datetime.datetime.utcnow())


# ============================================================================
class GzippingWrapper(object):
    def __init__(self, out):
        self.compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS + 16)
        self.out = out

    def write(self, buff):
        #if isinstance(buff, str):
        #    buff = buff.encode('utf-8')
        buff = self.compressor.compress(buff)
        self.out.write(buff)

    def flush(self):
        buff = self.compressor.flush()
        self.out.write(buff)
        self.out.flush()


# ============================================================================
class Digester(object):
    def __init__(self, type_='sha1'):
        self.type_ = type_
        self.digester = hashlib.new(type_)

    def update(self, buff):
        self.digester.update(buff)

    def __str__(self):
        return self.type_ + ':' + to_native_str(base64.b32encode(self.digester.digest()))


# ============================================================================
class BufferWARCWriter(BaseWARCWriter):
    def __init__(self, *args, **kwargs):
        super(BufferWARCWriter, self).__init__(*args, **kwargs)
        self.out = self._create_buffer()

    def _create_buffer(self):
        return tempfile.SpooledTemporaryFile(max_size=512*1024)

    def write_record(self, record):
        self._write_warc_record(self.out, record)

    def get_contents(self):
        pos = self.out.tell()
        self.out.seek(0)
        buff = self.out.read()
        self.out.seek(pos)
        return buff


# ============================================================================
class FileWARCWriter(BufferWARCWriter):
    def __init__(self, *args, **kwargs):
        file_or_buff = None
        if len(args) > 0:
            file_or_buff = args[0]
        else:
            file_or_buff = kwargs.get('file')

        if isinstance(file_or_buff, str):
            self.out = open(file_or_buff, 'rb')
        elif hasattr(file_or_buff, 'read'):
            self.out = file_or_buff
        else:
            raise Exception('file must be a readable or valid filename')



