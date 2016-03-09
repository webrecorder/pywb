from requests import request as remote_request
from requests.structures import CaseInsensitiveDict

from webagg.liverec import ReadFullyStream
from webagg.responseloader import StreamIter
from webagg.inputrequest import DirectWSGIInputRequest

from pywb.utils.statusandheaders import StatusAndHeadersParser
from pywb.warc.recordloader import ArcWarcRecord
from pywb.warc.recordloader import ArcWarcRecordLoader

from recorder.warcrecorder import SingleFileWARCRecorder, PerRecordWARCRecorder
from recorder.redisindexer import WritableRedisIndexer

from six.moves.urllib.parse import parse_qsl

import json
import tempfile

import traceback

import gevent.queue
import gevent


#==============================================================================
write_queue = gevent.queue.Queue()


#==============================================================================
class RecorderApp(object):
    def __init__(self, upstream_host, writer):
        self.upstream_host = upstream_host

        self.writer = writer
        self.parser = StatusAndHeadersParser([], verify=False)

        gevent.spawn(self._do_write)

    def _do_write(self):
        while True:
            try:
                result = write_queue.get()
                req = None
                resp = None
                req_head, req_pay, resp_head, resp_pay, params = result

                req = self._create_req_record(req_head, req_pay, 'request')
                resp = self._create_resp_record(resp_head, resp_pay, 'response')

                self.writer.write_req_resp(req, resp, params)

            except:
                traceback.print_exc()

            finally:
                try:
                    if req:
                        req.stream.close()

                    if resp:
                        resp.stream.close()
                except Exception as e:
                    traceback.print_exc()

    def _create_req_record(self, req_headers, payload, type_, ct=''):
        len_ = payload.tell()
        payload.seek(0)

        #warc_headers = StatusAndHeaders('WARC/1.0', req_headers.items())
        warc_headers = req_headers

        status_headers = self.parser.parse(payload)

        record = ArcWarcRecord('warc', type_, warc_headers, payload,
                                status_headers, ct, len_)
        return record

    def _create_resp_record(self, req_headers, payload, type_, ct=''):
        len_ = payload.tell()
        payload.seek(0)

        warc_headers = self.parser.parse(payload)
        warc_headers = CaseInsensitiveDict(warc_headers.headers)

        status_headers = self.parser.parse(payload)

        record = ArcWarcRecord('warc', type_, warc_headers, payload,
                              status_headers, ct, len_)
        return record

    def send_error(self, exc, start_response):
        message = json.dumps({'error': repr(exc)})
        headers = [('Content-Type', 'application/json; charset=utf-8'),
                   ('Content-Length', str(len(message)))]

        start_response('400 Bad Request', headers)
        return message

    def __call__(self, environ, start_response):
        request_uri = environ.get('REQUEST_URI')

        input_req = DirectWSGIInputRequest(environ)
        headers = input_req.get_req_headers()
        method = input_req.get_req_method()

        params = dict(parse_qsl(environ.get('QUERY_STRING')))

        req_stream = Wrapper(input_req.get_req_body(), headers, None)

        try:
            res = remote_request(url=self.upstream_host + request_uri,
                                 method=method,
                                 data=req_stream,
                                 headers=headers,
                                 allow_redirects=False,
                                 stream=True)
        except Exception as e:
            traceback.print_exc()
            return self.send_error(e, start_response)

        start_response('200 OK', list(res.headers.items()))

        resp_stream = Wrapper(res.raw, res.headers, req_stream, params)

        return StreamIter(ReadFullyStream(resp_stream))


#==============================================================================
class Wrapper(object):
    def __init__(self, stream, rec_headers, req_obj=None,
                 params=None):
        self.stream = stream
        self.out = self._create_buffer()
        self.headers = CaseInsensitiveDict(rec_headers)
        for n in rec_headers.keys():
            if not n.upper().startswith('WARC-'):
                del self.headers[n]

        self.req_obj = req_obj
        self.params = params

    def _create_buffer(self):
        return tempfile.SpooledTemporaryFile(max_size=512*1024)

    def read(self, limit=-1):
        buff = self.stream.read()
        self.out.write(buff)
        return buff

    def close(self):
        try:
            self.stream.close()
        except:
            traceback.print_exc()

        if not self.req_obj:
            return

        try:
            entry = (self.req_obj.headers, self.req_obj.out,
                     self.headers, self.out, self.params)
            write_queue.put(entry)
            self.req_obj = None
        except:
            traceback.print_exc()


#==============================================================================
application = RecorderApp('http://localhost:8080',
                PerRecordWARCRecorder('./warcs/{user}/{coll}/',
                  dedup_index=WritableRedisIndexer('redis://localhost/2/{user}:{coll}:cdxj', 'recorder')))

