from webagg.responseloader import  WARCPathLoader, LiveWebLoader, UpstreamProxyLoader
from webagg.utils import MementoUtils
from pywb.utils.wbexception import BadRequestException, WbException
from pywb.utils.wbexception import NotFoundException


#=============================================================================
def to_cdxj(cdx_iter, fields):
    content_type = 'text/x-cdxj'
    return content_type, (cdx.to_cdxj(fields) for cdx in cdx_iter)

def to_json(cdx_iter, fields):
    content_type = 'application/x-ndjson'
    return content_type, (cdx.to_json(fields) for cdx in cdx_iter)

def to_text(cdx_iter, fields):
    content_type = 'text/plain'
    return content_type, (cdx.to_text(fields) for cdx in cdx_iter)

def to_link(cdx_iter, fields):
    content_type = 'application/link'
    return content_type, MementoUtils.make_timemap(cdx_iter)


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
        return dict(modes=['list_sources', 'index'])

    def _load_index_source(self, params):
        url = params.get('url')
        if not url:
            errs = dict(last_exc=BadRequestException('The "url" param is required'))
            return None, errs

        input_req = params.get('_input_req')
        if input_req:
            params['alt_url'] = input_req.include_post_query(url)

        return self.index_source(params)

    def __call__(self, params):
        mode = params.get('mode', 'index')
        if mode == 'list_sources':
            return {}, self.index_source.get_source_list(params), {}

        if mode != 'index':
            return {}, self.get_supported_modes(), {}

        output = params.get('output', self.DEF_OUTPUT)
        fields = params.get('fields')

        handler = self.OUTPUTS.get(output)
        if not handler:
            errs = dict(last_exc=BadRequestException('output={0} not supported'.format(output)))
            return None, None, errs

        cdx_iter, errs = self._load_index_source(params)
        if not cdx_iter:
            return None, None, errs

        content_type, res = handler(cdx_iter, fields)
        out_headers = {'Content-Type': content_type}
        return out_headers, res, errs


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

        cdx_iter, errs = self._load_index_source(params)
        if not cdx_iter:
            return None, None, errs

        last_exc = None

        for cdx in cdx_iter:
            for loader in self.resource_loaders:
                try:
                    out_headers, resp = loader(cdx, params)
                    if resp is not None:
                        return out_headers, resp, errs
                except WbException as e:
                    last_exc = e
                    errs[str(loader)] = repr(e)

        if last_exc:
            errs['last_exc'] = last_exc

        return None, None, errs


#=============================================================================
class DefaultResourceHandler(ResourceHandler):
    def __init__(self, index_source, warc_paths=''):
        loaders = [WARCPathLoader(warc_paths, index_source),
                   UpstreamProxyLoader(),
                   LiveWebLoader(),
                  ]
        super(DefaultResourceHandler, self).__init__(index_source, loaders)


#=============================================================================
class HandlerSeq(object):
    def __init__(self, handlers):
        self.handlers = handlers

    def get_supported_modes(self):
        if self.handlers:
            return self.handlers[0].get_supported_modes()
        else:
            return {}

    def __call__(self, params):
        all_errs = {}
        for handler in self.handlers:
            out_headers, res, errs = handler(params)
            all_errs.update(errs)
            if res is not None:
                return out_headers, res, all_errs

        return None, None, all_errs


