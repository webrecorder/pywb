#from gevent import monkey; monkey.patch_all()
from webagg.utils import ReadFullyStream, StreamIter
from webagg.inputrequest import DirectWSGIInputRequest

from pywb.utils.statusandheaders import StatusAndHeadersParser
from pywb.warc.recordloader import ArcWarcRecord
from pywb.warc.recordloader import ArcWarcRecordLoader

from recorder.warcrecorder import SingleFileWARCRecorder, PerRecordWARCRecorder
from recorder.redisindexer import WritableRedisIndexer

from six.moves.urllib.parse import parse_qsl

import json
import tempfile
import re

from requests.structures import CaseInsensitiveDict
import requests

import traceback

import gevent.queue
import gevent


#==============================================================================
class RecorderApp(object):
    def __init__(self, upstream_host, writer, accept_colls='.*'):
        self.upstream_host = upstream_host

        self.writer = writer
        self.parser = StatusAndHeadersParser([], verify=False)

        self.write_queue = gevent.queue.Queue()
        gevent.spawn(self._write_loop)

        self.rx_accept_colls = re.compile(accept_colls)

    def _write_loop(self):
        while True:
            self._write_one()

    def _write_one(self):
        req = None
        resp = None
        try:
            result = self.write_queue.get()

            req_head, req_pay, resp_head, resp_pay, params = result

            if not self.rx_accept_colls.match(resp_head.get('WebAgg-Source-Coll', '')):
                return

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

        warc_headers = req_headers
        status_headers = self.parser.parse(payload)

        record = ArcWarcRecord('warc', type_, warc_headers, payload,
                                status_headers, ct, len_)
        return record

    def _create_resp_record(self, resp_headers, payload, type_, ct=''):
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
        return [message.encode('utf-8')]

    def __call__(self, environ, start_response):
        input_req = DirectWSGIInputRequest(environ)
        headers = input_req.get_req_headers()
        method = input_req.get_req_method()
        request_uri = input_req.get_full_request_uri()

        input_buff = input_req.get_req_body()

        params = dict(parse_qsl(environ.get('QUERY_STRING')))

        req_stream = ReqWrapper(input_buff, headers)
        data = None
        if input_buff:
            data = req_stream

        try:
            res = requests.request(url=self.upstream_host + request_uri,
                                 method=method,
                                 data=data,
                                 headers=headers,
                                 allow_redirects=False,
                                 stream=True)
        except Exception as e:
            traceback.print_exc()
            return self.send_error(e, start_response)

        start_response('200 OK', list(res.headers.items()))

        resp_stream = RespWrapper(res.raw, res.headers, req_stream, params, self.write_queue)

        return StreamIter(ReadFullyStream(resp_stream))


#==============================================================================
class Wrapper(object):
    def __init__(self, stream):
        self.stream = stream
        self.out = self._create_buffer()

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
        finally:
            self._after_close()

    def _after_close(self):
        pass


#==============================================================================
class RespWrapper(Wrapper):
    def __init__(self, stream, headers, req,
                 params, queue):

        super(RespWrapper, self).__init__(stream)
        self.headers = headers
        self.req = req
        self.params = params
        self.queue = queue

    def _after_close(self):
        if not self.req:
            return

        try:
            entry = (self.req.headers, self.req.out,
                     self.headers, self.out, self.params)
            self.queue.put(entry)
            self.req = None
        except:
            traceback.print_exc()


#==============================================================================
class ReqWrapper(Wrapper):
    def __init__(self, stream, req_headers):
        super(ReqWrapper, self).__init__(stream)
        self.headers = CaseInsensitiveDict(req_headers)
        for n in req_headers.keys():
            if not n.upper().startswith('WARC-'):
                del self.headers[n]


