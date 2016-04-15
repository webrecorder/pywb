import tempfile
import uuid
import base64
import hashlib
import datetime
import zlib
import sys
import os
import six

import traceback

from collections import OrderedDict

from socket import gethostname
from io import BytesIO

import fcntl

from pywb.utils.loaders import LimitReader, to_native_str
from pywb.utils.bufferedreaders import BufferedReader
from pywb.utils.timeutils import timestamp20_now, datetime_to_iso_date

from pywb.warc.recordloader import ArcWarcRecord

from webagg.utils import ParamFormatter, res_template

from recorder.filters import ExcludeNone


# ============================================================================
class BaseWARCWriter(object):
    WARC_RECORDS = {'warcinfo': 'application/warc-fields',
         'response': 'application/http; msgtype=response',
         'revisit': 'application/http; msgtype=response',
         'request': 'application/http; msgtype=request',
         'metadata': 'application/warc-fields',
        }

    REVISIT_PROFILE = 'http://netpreserve.org/warc/1.0/revisit/uri-agnostic-identical-payload-digest'

    BUFF_SIZE = 8192

    FILE_TEMPLATE = 'rec-{timestamp}-{hostname}.warc.gz'

    def __init__(self, gzip=True, dedup_index=None, name='recorder',
                 header_filter=ExcludeNone(), *args, **kwargs):
        self.gzip = gzip
        self.dedup_index = dedup_index
        self.rec_source_name = name
        self.header_filter = header_filter
        self.hostname = gethostname()

    def ensure_digest(self, record):
        block_digest = record.rec_headers.get('WARC-Block-Digest')
        payload_digest = record.rec_headers.get('WARC-Payload-Digest')
        if block_digest and payload_digest:
            return

        block_digester = self._create_digester()
        payload_digester = self._create_digester()

        pos = record.stream.tell()

        block_digester.update(record.status_headers.headers_buff)

        while True:
            buf = record.stream.read(self.BUFF_SIZE)
            if not buf:
                break

            block_digester.update(buf)
            payload_digester.update(buf)

        record.stream.seek(pos)
        record.rec_headers['WARC-Block-Digest'] = str(block_digester)
        record.rec_headers['WARC-Payload-Digest'] = str(payload_digester)

    def _create_digester(self):
        return Digester('sha1')

    def _set_header_buff(self, record):
        exclude_list = self.header_filter(record)
        buff = record.status_headers.to_bytes(exclude_list)
        record.status_headers.headers_buff = buff

    def write_req_resp(self, req, resp, params):
        url = resp.rec_headers.get('WARC-Target-URI')
        dt = resp.rec_headers.get('WARC-Date')

        if not req.rec_headers.get('WARC-Record-ID'):
            req.rec_headers['WARC-Record-ID'] = self._make_warc_id()

        req.rec_headers['WARC-Target-URI'] = url
        req.rec_headers['WARC-Date'] = dt
        req.rec_headers['WARC-Type'] = 'request'
        #req.rec_headers['Content-Type'] = req.content_type

        resp_id = resp.rec_headers.get('WARC-Record-ID')
        if resp_id:
            req.rec_headers['WARC-Concurrent-To'] = resp_id

        self._set_header_buff(req)
        self._set_header_buff(resp)

        self.ensure_digest(resp)

        resp = self._check_revisit(resp, params)
        if not resp:
            print('Skipping due to dedup')
            return

        params['_formatter'] = ParamFormatter(params, name=self.rec_source_name)
        self._do_write_req_resp(req, resp, params)

    def create_warcinfo_record(self, filename, **kwargs):
        headers = {}
        headers['WARC-Record_ID'] = self._make_warc_id()
        headers['WARC-Type'] = 'warcinfo'
        if filename:
            headers['WARC-Filename'] = filename
        headers['WARC-Date'] = datetime_to_iso_date(datetime.datetime.utcnow())

        warcinfo = BytesIO()
        for n, v in six.iteritems(kwargs):
            self._header(warcinfo, n, v)

        warcinfo.seek(0)

        record = ArcWarcRecord('warc', 'warcinfo', headers, warcinfo,
                               None, '', len(warcinfo.getbuffer()))

        return record

    def _check_revisit(self, record, params):
        if not self.dedup_index:
            return record

        try:
            url = record.rec_headers.get('WARC-Target-URI')
            digest = record.rec_headers.get('WARC-Payload-Digest')
            iso_dt = record.rec_headers.get('WARC-Date')
            result = self.dedup_index.lookup_revisit(params, digest, url, iso_dt)
        except Exception as e:
            traceback.print_exc()
            result = None

        if result == 'skip':
            return None

        if isinstance(result, tuple) and result[0] == 'revisit':
            record.rec_headers['WARC-Type'] = 'revisit'
            record.rec_headers['WARC-Profile'] = self.REVISIT_PROFILE

            record.rec_headers['WARC-Refers-To-Target-URI'] = result[1]
            record.rec_headers['WARC-Refers-To-Date'] = result[2]

        return record

    def _write_warc_record(self, out, record):
        if self.gzip:
            out = GzippingWrapper(out)

        self._line(out, b'WARC/1.0')

        for n, v in six.iteritems(record.rec_headers):
            if n.lower() in ('content-length', 'content-type'):
                continue

            self._header(out, n, v)

        content_type = record.content_type
        if not content_type:
            content_type = self.WARC_RECORDS[record.rec_headers['WARC-Type']]

        self._header(out, 'Content-Type', record.content_type)

        if record.rec_headers['WARC-Type'] == 'revisit':
            http_headers_only = True
        else:
            http_headers_only = False

        if record.length:
            actual_len = 0
            if record.status_headers:
                actual_len = len(record.status_headers.headers_buff)

            if not http_headers_only:
                diff = record.stream.tell() - actual_len
                actual_len = record.length - diff

            self._header(out, 'Content-Length', str(actual_len))

            # add empty line
            self._line(out, b'')

            # write headers buffer, if any
            if record.status_headers:
                out.write(record.status_headers.headers_buff)

            if not http_headers_only:
                out.write(record.stream.read())

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

    @staticmethod
    def _make_warc_id(id_=None):
        if not id_:
            id_ = uuid.uuid1()
        return '<urn:uuid:{0}>'.format(id_)


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
class MultiFileWARCWriter(BaseWARCWriter):
    def __init__(self, dir_template, filename_template=None, max_size=0,
                 *args, **kwargs):
        super(MultiFileWARCWriter, self).__init__(*args, **kwargs)

        if not filename_template:
            dir_template, filename_template = os.path.split(dir_template)
            dir_template += os.path.sep

        if not filename_template:
            filename_template = self.FILE_TEMPLATE

        self.dir_template = dir_template
        self.filename_template = filename_template
        self.max_size = max_size

        self.fh_cache = {}

    def _open_file(self, dir_, params):
        timestamp = timestamp20_now()

        filename = dir_ + res_template(self.filename_template, params,
                                       hostname=self.hostname,
                                       timestamp=timestamp)

        path, name = os.path.split(filename)

        try:
            os.makedirs(path)
        except:
            pass

        fh = open(filename, 'a+b')

        if self.dedup_index:
            self.dedup_index.add_warc_file(filename, params)

        return fh, filename

    def _close_file(self, fh):
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()

    def close_file(self, full_dir):
        #full_dir = res_template(self.dir_template, params)
        result = self.fh_cache.pop(full_dir, None)
        if not result:
            return

        out, filename = result
        self._close_file(out)
        return filename

    def _is_write_resp(self, resp, params):
        return True

    def _is_write_req(self, req, params):
        return True

    def _do_write_req_resp(self, req, resp, params):
        full_dir = res_template(self.dir_template, params)

        result = self.fh_cache.get(full_dir)

        close_file = False

        if result:
            out, filename = result
            is_new = False
        else:
            out, filename = self._open_file(full_dir, params)
            is_new = True

        try:
            url = resp.rec_headers.get('WARC-Target-URI')
            print('Writing req/resp {0} to {1} '.format(url, filename))

            start = out.tell()

            if self._is_write_resp(resp, params):
                self._write_warc_record(out, resp)

            if self._is_write_req(req, params):
                self._write_warc_record(out, req)

            out.flush()

            new_size = out.tell()

            out.seek(start)

            if self.dedup_index:
                self.dedup_index.add_urls_to_index(out, params,
                                                   filename,
                                                   new_size - start)

        except Exception as e:
            traceback.print_exc()
            close_file = True

        finally:
            # check for rollover
            if self.max_size and new_size > self.max_size:
                close_file = True

            if close_file:
                self._close_file(out)
                if not is_new:
                    self.fh_cache.pop(full_dir, None)

            elif is_new:
                fcntl.flock(out, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.fh_cache[full_dir] = (out, filename)

    def close(self):
        for n, v in self.fh_cache.items():
            out, filename = v
            self._close_file(out)

        self.fh_cache = {}


# ============================================================================
class PerRecordWARCWriter(MultiFileWARCWriter):
    def __init__(self, *args, **kwargs):
        kwargs['max_size'] = 1
        super(PerRecordWARCWriter, self).__init__(*args, **kwargs)


# ============================================================================
class SimpleTempWARCWriter(BaseWARCWriter):
    def __init__(self, *args, **kwargs):
        super(SimpleTempWARCWriter, self).__init__(*args, **kwargs)
        self.out = self._create_buffer()

    def _create_buffer(self):
        return tempfile.SpooledTemporaryFile(max_size=512*1024)

    def _do_write_req_resp(self, req, resp, params):
        self._write_warc_record(self.out, resp)
        self._write_warc_record(self.out, req)

    def write_record(self, record):
        self._write_warc_record(self.out, record)

    def get_buffer(self):
        pos = self.out.tell()
        self.out.seek(0)
        buff = self.out.read()
        self.out.seek(pos)
        return buff
