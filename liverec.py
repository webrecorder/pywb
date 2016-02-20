from io import BytesIO

try:
    import httplib
except ImportError:
    import http.client as httplib


orig_connection = httplib.HTTPConnection

from contextlib import contextmanager

import ssl
from array import array

from time import sleep


BUFF_SIZE = 8192


# ============================================================================
class RecordingStream(object):
    def __init__(self, fp, recorder):
        self.fp = fp
        self.recorder = recorder
        self.incomplete = False

        if hasattr(self.fp, 'unread'):
            self.unread = self.fp.unread

        if hasattr(self.fp, 'tell'):
            self.tell = self.fp.tell

    def read(self, *args, **kwargs):
        buff = self.fp.read(*args, **kwargs)
        self.recorder.write_response_buff(buff)
        return buff

    def readinto(self, buff):
        res = self.fp.readinto(buff)
        self.recorder.write_response_buff(buff)
        return res

    def readline(self, maxlen=None):
        line = self.fp.readline(maxlen)
        self.recorder.write_response_header_line(line)
        return line

    def flush(self):
        self.fp.flush()

    def close(self):
        try:
            self.recorder.finish_response(self.incomplete)
        except Exception as e:
            import traceback
            traceback.print_exc()

        res = self.fp.close()
        return res


# ============================================================================
class RecordingHTTPResponse(httplib.HTTPResponse):
    def __init__(self, recorder, *args, **kwargs):
        httplib.HTTPResponse.__init__(self, *args, **kwargs)
        self.fp = RecordingStream(self.fp, recorder)

    def mark_incomplete(self):
        self.fp.incomplete = True


# ============================================================================
class RecordingHTTPConnection(httplib.HTTPConnection):
    global_recorder_maker = None

    def __init__(self, *args, **kwargs):
        orig_connection.__init__(self, *args, **kwargs)
        if not self.global_recorder_maker:
            self.recorder = None
        else:
            self.recorder = self.global_recorder_maker()

            def make_recording_response(*args, **kwargs):
                return RecordingHTTPResponse(self.recorder, *args, **kwargs)

            self.response_class = make_recording_response

    def send(self, data):
        if not self.recorder:
            orig_connection.send(self, data)
            return

        if hasattr(data,'read') and not isinstance(data, array):
            url = None
            while True:
                buff = data.read(self.BUFF_SIZE)
                if not buff:
                    break

                orig_connection.send(self, buff)
                self.recorder.write_request(url, buff)
        else:
            orig_connection.send(self, data)
            self.recorder.write_request(self, data)


    def get_url(self, data):
        try:
            buff = BytesIO(data)
            line = buff.readline()

            path = line.split(' ', 2)[1]
            host = self.host
            port = self.port
            scheme = 'https' if isinstance(self.sock, ssl.SSLSocket) else 'http'

            url = scheme + '://' + host
            if (scheme == 'https' and port != '443') and (scheme == 'http' and port != '80'):
                url += ':' + port

            url += path
        except Exception as e:
            raise

        return url


    def request(self, *args, **kwargs):
        #if self.recorder:
        #    self.recorder.start_request(self)

        res = orig_connection.request(self, *args, **kwargs)

        if self.recorder:
            self.recorder.finish_request(self.sock)

        return res


# ============================================================================
class BaseRecorder(object):
    def write_request(self, conn, buff):
        #url = conn.get_url()
        pass

    def write_response_header_line(self, line):
        pass

    def write_response_buff(self, buff):
        pass

    def finish_request(self, socket):
        pass

    def finish_response(self, incomplete=False):
        pass

#=================================================================
class ReadFullyStream(object):
    def __init__(self, stream):
        self.stream = stream

    def read(self, *args, **kwargs):
        try:
            return self.stream.read(*args, **kwargs)
        except:
            self.mark_incomplete()
            raise

    def readline(self, *args, **kwargs):
        try:
            return self.stream.readline(*args, **kwargs)
        except:
            self.mark_incomplete()
            raise

    def mark_incomplete(self):
        if (hasattr(self.stream, '_fp') and
            hasattr(self.stream._fp, 'mark_incomplete')):
            self.stream._fp.mark_incomplete()

    def close(self):
        try:
            while True:
                buff = self.stream.read(BUFF_SIZE)
                sleep(0)
                if not buff:
                    break

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.mark_incomplete()
        finally:
            self.stream.close()


# ============================================================================
httplib.HTTPConnection = RecordingHTTPConnection
# ============================================================================

class DefaultRecorderMaker(object):
    def __call__(self):
        return BaseRecorder()


class FixedRecorder(object):
    def __init__(self, recorder):
        self.recorder = recorder

    def __call__(self):
        return self.recorder

@contextmanager
def record_requests(url, recorder_maker):
    RecordingHTTPConnection.global_recorder_maker = recorder_maker
    yield
    RecordingHTTPConnection.global_recorder_maker = None

@contextmanager
def orig_requests():
    httplib.HTTPConnection = orig_connection
    yield
    httplib.HTTPConnection = RecordingHTTPConnection


import requests as patched_requests

def request(url, method='GET', recorder=None, recorder_maker=None, session=patched_requests, **kwargs):
    if kwargs.get('skip_recording'):
        recorder_maker = None
    elif recorder:
        recorder_maker = FixedRecorder(recorder)
    elif not recorder_maker:
        recorder_maker = DefaultRecorderMaker()

    with record_requests(url, recorder_maker):
        kwargs['allow_redirects'] = False
        r = session.request(method=method,
                            url=url,
                            **kwargs)

    return r
