from rezag.responseloader import  WARCPathLoader, LiveWebLoader
from rezag.utils import MementoUtils
from pywb.utils.wbexception import BadRequestException, WbException
from pywb.utils.wbexception import NotFoundException
from bottle import response


#=============================================================================
def to_cdxj(cdx_iter, fields):
    response.headers['Content-Type'] = 'application/x-cdxj'
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

    def get_supported_modes(self):
        return dict(modes=['list_modes', 'list_sources', 'index'])

    def _load_index_source(self, params):
        url = params.get('url')
        if not url:
            raise BadRequestException('The "url" param is required')

        input_req = params.get('_input_req')
        if input_req:
            params['alt_url'] = input_req.include_post_query(url)

        return self.index_source(params)

    def __call__(self, params):
        mode = params.get('mode', 'index')
        if mode == 'list_sources':
            return self.index_source.get_source_list(params)

        if mode == 'list_modes' or mode != 'index':
            return self.get_supported_modes()

        output = params.get('output', self.DEF_OUTPUT)
        fields = params.get('fields')

        handler = self.OUTPUTS.get(output)
        if not handler:
            raise BadRequestException('output={0} not supported'.format(output))

        cdx_iter = self._load_index_source(params)
        res = handler(cdx_iter, fields)
        return res


#=============================================================================
class ResourceHandler(IndexHandler):
    def __init__(self, index_source, resource_loaders):
        super(ResourceHandler, self).__init__(index_source)
        self.resource_loaders = resource_loaders

    def get_supported_modes(self):
        res = super(ResourceHandler, self).get_supported_modes()
        res['modes'].append('resource')
        return res

    def __call__(self, params):
        if params.get('mode', 'resource') != 'resource':
            return super(ResourceHandler, self).__call__(params)

        cdx_iter = self._load_index_source(params)
        last_exc = None

        for cdx in cdx_iter:
            for loader in self.resource_loaders:
                try:
                    resp = loader(cdx, params)
                    if resp is not None:
                        return resp
                except WbException as e:
                    last_exc = e

        if last_exc:
            raise last_exc
            #raise ArchiveLoadFailed('Resource Found, could not be Loaded')
        else:
            raise NotFoundException('No Resource Found')


#=============================================================================
class DefaultResourceHandler(ResourceHandler):
    def __init__(self, index_source, warc_paths=''):
        loaders = [WARCPathLoader(warc_paths, index_source),
                   LiveWebLoader()
                  ]
        super(DefaultResourceHandler, self).__init__(index_source, loaders)


#=============================================================================
class HandlerSeq(object):
    def __init__(self, handlers):
        self.handlers = handlers

    def __call__(self, params):
        last_exc = None
        for handler in self.handlers:
            try:
                res = handler(params)
                if res is not None:
                    return res
            except WbException as e:
                last_exc = e

        if last_exc:
            raise last_exc
        else:
            raise NotFoundException('No Resource Found')
