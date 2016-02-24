from liverec import BaseRecorder
from liverec import request as remote_request

from pywb.warc.recordloader import ArcWarcRecordLoader, ArchiveLoadFailed
from pywb.utils.timeutils import timestamp_to_datetime, datetime_to_http_date
from pywb.warc.resolvingloader import ResolvingLoader

from io import BytesIO
from bottle import response

import uuid
from utils import MementoUtils


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
class WARCPathLoader(object):
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
                    full_path = path.format(**cdx)
                    return full_path
                except KeyError:
                    return None

            yield check


    def __call__(self, cdx, params):
        if not cdx.get('filename') or cdx.get('offset') is None:
            return None

        failed_files = []
        headers, payload = (self.resolve_loader.
                             load_headers_and_payload(cdx,
                                                      failed_files,
                                                      self.cdx_source))

        if headers != payload:
            headers.stream.close()

        record = payload

        for n, v in record.rec_headers.headers:
            response.headers[n] = v

        response.headers['WARC-Coll'] = cdx.get('source')

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

    def __call__(self, cdx, params):
        load_url = cdx.get('load_url')
        if not load_url:
            return None

        recorder = HeaderRecorder(self.SKIP_HEADERS)

        input_req = params['_input_req']

        req_headers = input_req.get_req_headers(cdx['url'])

        dt = timestamp_to_datetime(cdx['timestamp'])

        if not cdx.get('is_live'):
            req_headers['Accept-Datetime'] = datetime_to_http_date(dt)

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


#=============================================================================
def to_cdxj(cdx_iter, fields):
    response.headers['Content-Type'] = 'text/x-cdxj'
    return [cdx.to_cdxj(fields) for cdx in cdx_iter]

def to_json(cdx_iter, fields):
    response.headers['Content-Type'] = 'application/x-ndjson'
    return [cdx.to_json(fields) for cdx in cdx_iter]

def to_text(cdx_iter, fields):
    response.headers['Content-Type'] = 'text/plain'
    return [cdx.to_text(fields) for cdx in cdx_iter]

def to_link(cdx_iter, fields):
    response.headers['Content-Type'] = 'application/link'
    return MementoUtils.make_timemap(cdx_iter)


#=============================================================================
class IndexLoader(object):
    OUTPUTS = {
        'cdxj': to_cdxj,
        'json': to_json,
        'text': to_text,
        'link': to_link,
    }

    DEF_OUTPUT = 'cdxj'

    def __init__(self, index_source):
        self.index_source = index_source

    def __call__(self, params):
        cdx_iter = self.index_source(params)

        output = params.get('output', self.DEF_OUTPUT)
        fields = params.get('fields')

        handler = self.OUTPUTS.get(output)
        if not handler:
            handler = self.OUTPUTS[self.DEF_OUTPUT]

        res = handler(cdx_iter, fields)
        return res


#=============================================================================
class ResourceLoader(IndexLoader):
    def __init__(self, index_source, resource_loaders):
        super(ResourceLoader, self).__init__(index_source)
        self.resource_loaders = resource_loaders

    def __call__(self, params):
        output = params.get('output')
        if output != 'resource':
            return super(ResourceLoader, self).__call__(params)

        cdx_iter = self.index_source(params)

        any_found = False

        for cdx in cdx_iter:
            any_found = True
            cdx['coll'] = params.get('coll', '')

            for loader in self.resource_loaders:
                try:
                    resp = loader(cdx, params)
                    if resp:
                        return resp
                except ArchiveLoadFailed as e:
                    print(e)
                    pass

        if any_found:
            raise ArchiveLoadFailed('Resource Found, could not be Loaded')
        else:
            raise ArchiveLoadFailed('No Resource Found')


#=============================================================================
class DefaultResourceLoader(ResourceLoader):
    def __init__(self, index_source, warc_paths=''):
        loaders = [WARCPathLoader(warc_paths, index_source),
                   LiveWebLoader()
                  ]
        super(DefaultResourceLoader, self).__init__(index_source, loaders)


#=============================================================================
class LoaderSeq(object):
    def __init__(self, loaders):
        self.loaders = loaders

    def __call__(self, params):
        for loader in self.loaders:
            try:
                res = loader(params)
                if res:
                    return res
            except ArchiveLoadFailed:
                pass

        raise ArchiveLoadFailed('No Resource Found')


