from rezag.responseloader import  WARCPathHandler, LiveWebHandler
from rezag.utils import MementoUtils
from pywb.warc.recordloader import ArchiveLoadFailed
from bottle import response


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
class IndexHandler(object):
    OUTPUTS = {
        'cdxj': to_cdxj,
        'json': to_json,
        'text': to_text,
        'link': to_link,
    }

    DEF_OUTPUT = 'cdxj'

    def __init__(self, index_source, opts=None):
        self.index_source = index_source
        self.opts = opts or {}

    def __call__(self, params):
        if params.get('mode') == 'sources':
            srcs = self.index_source.get_sources(params)
            result = [(name, str(value)) for name, value in srcs]
            result = {'sources': dict(result)}
            return result

        input_req = params.get('_input_req')
        if input_req:
            params['alt_url'] = input_req.include_post_query(params.get('url'))

        cdx_iter = self.index_source(params)

        output = params.get('output', self.DEF_OUTPUT)
        fields = params.get('fields')

        handler = self.OUTPUTS.get(output)
        if not handler:
            handler = self.OUTPUTS[self.DEF_OUTPUT]

        res = handler(cdx_iter, fields)
        return res


#=============================================================================
class ResourceHandler(IndexHandler):
    def __init__(self, index_source, resource_loaders):
        super(ResourceHandler, self).__init__(index_source)
        self.resource_loaders = resource_loaders

    def __call__(self, params):
        if params.get('mode', 'resource') != 'resource':
            return super(ResourceHandler, self).__call__(params)

        input_req = params.get('_input_req')
        if input_req:
            params['alt_url'] = input_req.include_post_query(params.get('url'))

        cdx_iter = self.index_source(params)

        any_found = False

        for cdx in cdx_iter:
            any_found = True

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
class DefaultResourceHandler(ResourceHandler):
    def __init__(self, index_source, warc_paths=''):
        loaders = [WARCPathHandler(warc_paths, index_source),
                   LiveWebHandler()
                  ]
        super(DefaultResourceHandler, self).__init__(index_source, loaders)


#=============================================================================
class HandlerSeq(object):
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
