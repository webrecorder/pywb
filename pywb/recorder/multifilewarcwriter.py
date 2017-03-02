import base64
import datetime
import os
import shutil

import traceback

import portalocker

from warcio.timeutils import timestamp20_now
from warcio.warcwriter import BaseWARCWriter

from pywb.webagg.utils import res_template


# ============================================================================
class MultiFileWARCWriter(BaseWARCWriter):
    FILE_TEMPLATE = 'rec-{timestamp}-{hostname}.warc.gz'

    def __init__(self, dir_template, filename_template=None, max_size=0,
                 max_idle_secs=1800, *args, **kwargs):
        super(MultiFileWARCWriter, self).__init__(*args, **kwargs)

        self.header_filter = kwargs.get('header_filter')

        if not filename_template:
            dir_template, filename_template = os.path.split(dir_template)
            dir_template += os.path.sep

        if not filename_template:
            filename_template = self.FILE_TEMPLATE

        self.dir_template = dir_template
        self.key_template = kwargs.get('key_template', self.dir_template)
        self.dedup_index = kwargs.get('dedup_index')
        self.filename_template = filename_template
        self.max_size = max_size
        if max_idle_secs > 0:
            self.max_idle_time = datetime.timedelta(seconds=max_idle_secs)
        else:
            self.max_idle_time = None

        self.fh_cache = {}

    def _check_revisit(self, record, params):
        if not self.dedup_index or record.rec_type != 'response':
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
            record = self.create_revisit_record(url, digest, result[1], result[2],
                                                http_headers=record.http_headers)

        return record

    def _set_header_buff(self, record):
        exclude_list = None
        if self.header_filter:
            exclude_list = self.header_filter(record)
        buff = record.http_headers.to_bytes(exclude_list)
        record.http_headers.headers_buff = buff

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
        resp = self._check_revisit(resp, params)
        if not resp:
            print('Skipping due to dedup')
            return

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

        new_size = start = 0

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

