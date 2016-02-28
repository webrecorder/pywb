from rezag.liverec import BaseRecorder
from rezag.liverec import request as remote_request

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

    try:
        stream.close()
    except:
        pass


#=============================================================================
class WARCPathHandler(object):
    def __init__(self, paths, cdx_source):
        self.paths = paths
        if isinstance(paths, str):
            self.paths = [paths]

        self.path_checks = list(self.warc_paths())

        self.resolve_loader = ResolvingLoader(self.path_checks,
                                              no_record_parse=True)
        self.cdx_source = cdx_source

    def warc_paths(self):
        for path in self.paths:
            def check(filename, cdx):
                try:
                    if hasattr(cdx, '_src_params') and cdx._src_params:
                        full_path = path.format(**cdx._src_params)
                    else:
                        full_path = path
                    full_path += filename
                    return full_path
                except KeyError:
                    return None

            yield check


    def __call__(self, cdx, params):
        if not cdx.get('filename') or cdx.get('offset') is None:
            return None

        cdx._src_params = params.get('_src_params')
        failed_files = []
        headers, payload = (self.resolve_loader.
                             load_headers_and_payload(cdx,
                                                      failed_files,
                                                      self.cdx_source))

        record = payload

        for n, v in record.rec_headers.headers:
            response.headers[n] = v

        response.headers['WARC-Coll'] = cdx.get('source')

        if headers != payload:
            response.headers['WARC-Target-URI'] = headers.rec_headers.get_header('WARC-Target-URI')
            response.headers['WARC-Date'] = headers.rec_headers.get_header('WARC-Date')
            response.headers['WARC-Refers-To-Target-URI'] = payload.rec_headers.get_header('WARC-Target-URI')
            response.headers['WARC-Refers-To-Date'] = payload.rec_headers.get_header('WARC-Date')
            headers.stream.close()

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
class LiveWebHandler(object):
    SKIP_HEADERS = (b'link',
                    b'memento-datetime',
                    b'content-location',
                    b'x-archive')

    def __call__(self, cdx, params):
        load_url = cdx.get('load_url')
        if not load_url:
            return None

        recorder = HeaderRecorder(self.SKIP_HEADERS)

        input_req = params['_input_req']

        req_headers = input_req.get_req_headers()

        dt = timestamp_to_datetime(cdx['timestamp'])

        if not cdx.get('is_live'):
            req_headers['Accept-Datetime'] = datetime_to_http_date(dt)

        # if different url, ensure origin is not set
        # may need to add other headers
        if load_url != cdx['url']:
            if 'Origin' in req_headers:
                splits = urlsplit(load_url)
                req_headers['Origin'] = splits.scheme + '://' + splits.netloc

        method = input_req.get_req_method()
        data = input_req.get_req_body()

        upstream_res = remote_request(url=load_url,
                                      method=method,
                                      recorder=recorder,
                                      stream=True,
                                      allow_redirects=False,
                                      headers=req_headers,
                                      data=data,
                                      timeout=params.get('_timeout'))

        resp_headers = recorder.get_header()

        response.headers['Content-Type'] = 'application/http; msgtype=response'

        #response.headers['WARC-Type'] = 'response'
        #response.headers['WARC-Record-ID'] = self._make_warc_id()
        response.headers['WARC-Target-URI'] = cdx['url']
        response.headers['WARC-Date'] = self._make_date(dt)
        response.headers['WARC-Coll'] = cdx.get('source', '')

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
