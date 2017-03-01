import tempfile
import uuid
import base64
import hashlib
import datetime
import zlib
import sys
import os
import six
import shutil

import traceback

from socket import gethostname
from io import BytesIO

import portalocker

from pywb.utils.loaders import LimitReader, to_native_str
from pywb.utils.bufferedreaders import BufferedReader
from pywb.utils.timeutils import timestamp20_now, datetime_to_iso_date

from pywb.utils.statusandheaders import StatusAndHeadersParser, StatusAndHeaders
from pywb.warc.recordloader import ArcWarcRecord
from pywb.warc.recordloader import ArcWarcRecordLoader

from pywb.webagg.utils import res_template, BUFF_SIZE


# ============================================================================
class BaseWARCWriter(object):
    WARC_RECORDS = {'warcinfo': 'application/warc-fields',
         'response': 'application/http; msgtype=response',
         'revisit': 'application/http; msgtype=response',
         'request': 'application/http; msgtype=request',
         'metadata': 'application/warc-fields',
        }

    REVISIT_PROFILE = 'http://netpreserve.org/warc/1.0/revisit/uri-agnostic-identical-payload-digest'

    FILE_TEMPLATE = 'rec-{timestamp}-{hostname}.warc.gz'

    WARC_VERSION = 'WARC/1.0'

    def __init__(self, gzip=True, dedup_index=None,
                 header_filter=None, *args, **kwargs):

        self.gzip = gzip
        self.dedup_index = dedup_index
        self.header_filter = header_filter
        self.hostname = gethostname()

        self.parser = StatusAndHeadersParser([], verify=False)
        self.warc_version = kwargs.get('warc_version', self.WARC_VERSION)

    @staticmethod
    def _iter_stream(stream):
        while True:
            buf = stream.read(BUFF_SIZE)
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

    def write_req_resp(self, req, resp, params):
        url = resp.rec_headers.get_header('WARC-Target-URI')
        dt = resp.rec_headers.get_header('WARC-Date')

        #req.rec_headers['Content-Type'] = req.content_type
        req.rec_headers.replace_header('WARC-Target-URI', url)
        req.rec_headers.replace_header('WARC-Date', dt)

        resp_id = resp.rec_headers.get_header('WARC-Record-ID')
        if resp_id:
            req.rec_headers.add_header('WARC-Concurrent-To', resp_id)

        resp = self._check_revisit(resp, params)
        if not resp:
            print('Skipping due to dedup')
            return

        self._do_write_req_resp(req, resp, params)

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

    def _check_revisit(self, record, params):
        if not self.dedup_index:
            return record

        try:
            url = record.rec_headers.get_header('WARC-Target-URI')
            digest = record.rec_headers.get_header('WARC-Payload-Digest')
            iso_dt = record.rec_headers.get_header('WARC-Date')
            result = self.dedup_index.lookup_revisit(params, digest, url, iso_dt)
        except Exception as e:
            traceback.print_exc()
            result = None

        if result == 'skip':
            return None

        if isinstance(result, tuple) and result[0] == 'revisit':
            record.rec_headers.replace_header('WARC-Type', 'revisit')
            record.rec_headers.add_header('WARC-Profile', self.REVISIT_PROFILE)

            record.rec_headers.add_header('WARC-Refers-To-Target-URI', result[1])
            record.rec_headers.add_header('WARC-Refers-To-Date', result[2])

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
class MultiFileWARCWriter(BaseWARCWriter):
    def __init__(self, dir_template, filename_template=None, max_size=0,
                 max_idle_secs=1800, *args, **kwargs):
        super(MultiFileWARCWriter, self).__init__(*args, **kwargs)

        if not filename_template:
            dir_template, filename_template = os.path.split(dir_template)
            dir_template += os.path.sep

        if not filename_template:
            filename_template = self.FILE_TEMPLATE

        self.dir_template = dir_template
        self.key_template = kwargs.get('key_template', self.dir_template)
        self.filename_template = filename_template
        self.max_size = max_size
        if max_idle_secs > 0:
            self.max_idle_time = datetime.timedelta(seconds=max_idle_secs)
        else:
            self.max_idle_time = None

        self.fh_cache = {}

    def get_new_filename(self, dir_, params):
        timestamp = timestamp20_now()

        randstr = base64.b32encode(os.urandom(5)).decode('utf-8')

        filename = dir_ + res_template(self.filename_template, params,
                                       hostname=self.hostname,
                                       timestamp=timestamp,
                                       random=randstr)

        return filename

    def allow_new_file(self, filename, params):
        return True

    def _open_file(self, filename, params):
        path, name = os.path.split(filename)

        try:
            os.makedirs(path)
        except:
            pass

        fh = open(filename, 'a+b')

        if self.dedup_index:
            self.dedup_index.add_warc_file(filename, params)

        return fh

    def _close_file(self, fh):
        try:
            portalocker.lock(fh, portalocker.LOCK_UN)
            fh.close()
        except Exception as e:
            print(e)

    def get_dir_key(self, params):
        return res_template(self.key_template, params)

    def close_key(self, dir_key):
        if isinstance(dir_key, dict):
            dir_key = self.get_dir_key(dir_key)

        result = self.fh_cache.pop(dir_key, None)
        if not result:
            return

        out, filename = result
        self._close_file(out)
        return filename

    def close_file(self, match_filename):
        for dir_key, out, filename in self.iter_open_files():
            if filename == match_filename:
                return self.close_key(dir_key)

    def _is_write_resp(self, resp, params):
        return True

    def _is_write_req(self, req, params):
        return True

    def write_record(self, record, params=None):
        params = params or {}
        self._do_write_req_resp(None, record, params)

    def _do_write_req_resp(self, req, resp, params):
        def write_callback(out, filename):
            #url = resp.rec_headers.get_header('WARC-Target-URI')
            #print('Writing req/resp {0} to {1} '.format(url, filename))

            if resp and self._is_write_resp(resp, params):
                self._write_warc_record(out, resp)

            if req and self._is_write_req(req, params):
                self._write_warc_record(out, req)

        return self._write_to_file(params, write_callback)

    def write_stream_to_file(self, params, stream):
        def write_callback(out, filename):
            #print('Writing stream to {0}'.format(filename))
            shutil.copyfileobj(stream, out)

        return self._write_to_file(params, write_callback)

    def _write_to_file(self, params, write_callback):
        full_dir = res_template(self.dir_template, params)
        dir_key = self.get_dir_key(params)

        result = self.fh_cache.get(dir_key)

        close_file = False

        if result:
            out, filename = result
            is_new = False
        else:
            filename = self.get_new_filename(full_dir, params)

            if not self.allow_new_file(filename, params):
                return False

            out = self._open_file(filename, params)

            is_new = True

        try:
            start = out.tell()

            write_callback(out, filename)

            out.flush()

            new_size = out.tell()

            out.seek(start)

            if self.dedup_index:
                self.dedup_index.add_urls_to_index(out, params,
                                                   filename,
                                                   new_size - start)

            return True

        except Exception as e:
            traceback.print_exc()
            close_file = True
            return False

        finally:
            # check for rollover
            if self.max_size and new_size > self.max_size:
                close_file = True

            if close_file:
                self._close_file(out)
                if not is_new:
                    self.fh_cache.pop(dir_key, None)

            elif is_new:
                portalocker.lock(out, portalocker.LOCK_EX | portalocker.LOCK_NB)
                self.fh_cache[dir_key] = (out, filename)

    def iter_open_files(self):
        for n, v in list(self.fh_cache.items()):
            out, filename = v
            yield n, out, filename

    def close(self):
        for dir_key, out, filename in self.iter_open_files():
            self._close_file(out)

        self.fh_cache = {}

    def close_idle_files(self):
        if not self.max_idle_time:
            return

        now = datetime.datetime.now()

        for dir_key, out, filename in self.iter_open_files():
            try:
                mtime = os.path.getmtime(filename)
            except:
                self.close_key(dir_key)
                return

            mtime = datetime.datetime.fromtimestamp(mtime)

            if (now - mtime) > self.max_idle_time:
                print('Closing idle ' + filename)
                self.close_key(dir_key)


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

    def write_record(self, record, params=None):
        self._write_warc_record(self.out, record)

    def get_buffer(self):
        pos = self.out.tell()
        self.out.seek(0)
        buff = self.out.read()
        self.out.seek(pos)
        return buff
