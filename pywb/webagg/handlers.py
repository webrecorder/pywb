from pywb.webagg.responseloader import  WARCPathLoader, LiveWebLoader, VideoLoader
from pywb.webagg.utils import MementoUtils
from pywb.utils.wbexception import BadRequestException, WbException
from pywb.utils.wbexception import NotFoundException
from warcio.recordloader import ArchiveLoadFailed

from pywb.cdx.query import CDXQuery
from pywb.cdx.cdxdomainspecific import load_domain_specific_cdx_rules

import six


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
class FuzzyMatcher(object):
    def __init__(self):
        res = load_domain_specific_cdx_rules('pywb/rules.yaml', True)
        self.url_canon, self.fuzzy_query = res

    def __call__(self, index_source, params):
        cdx_iter, errs = index_source(params)
        return self.do_fuzzy(cdx_iter, index_source, params), errs

    def do_fuzzy(self, cdx_iter, index_source, params):
        found = False
        for cdx in cdx_iter:
            found = True
            yield cdx

        fuzzy_query_params = None
        if not found:
            query = CDXQuery(params)
            fuzzy_query_params = self.fuzzy_query(query)

        if not fuzzy_query_params:
            return

        fuzzy_query_params.pop('alt_url', '')

        new_iter, errs = index_source(fuzzy_query_params)

        for cdx in new_iter:
            yield cdx


#=============================================================================
class IndexHandler(object):
    OUTPUTS = {
        'cdxj': to_cdxj,
        'json': to_json,
        'text': to_text,
        'link': to_link,
    }

    DEF_OUTPUT = 'cdxj'

    def __init__(self, index_source, opts=None, *args, **kwargs):
        self.index_source = index_source
        self.opts = opts or {}
        self.fuzzy = FuzzyMatcher()

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

        return self.fuzzy(self.index_source, params)

    def __call__(self, params):
        mode = params.get('mode', 'index')
        if mode == 'list_sources':
            return {}, self.index_source.get_source_list(params), {}

        if mode != 'index':
            return {}, self.get_supported_modes(), {}

        output = params.get('output', self.DEF_OUTPUT)
        fields = params.get('fields')

        if fields and isinstance(fields, str):
            fields = fields.split(',')

        handler = self.OUTPUTS.get(output, fields)
        if not handler:
            errs = dict(last_exc=BadRequestException('output={0} not supported'.format(output)))
            return None, None, errs

        cdx_iter, errs = self._load_index_source(params)
        if not cdx_iter:
            return None, None, errs

        content_type, res = handler(cdx_iter, fields)
        out_headers = {'Content-Type': content_type}

        def check_str(lines):
            for line in lines:
                if isinstance(line, six.text_type):
                    line = line.encode('utf-8')
                yield line

        return out_headers, check_str(res), errs


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
                except (WbException, ArchiveLoadFailed) as e:
                    last_exc = e
                    errs[str(loader)] = str(e)

        if last_exc:
            errs['last_exc'] = last_exc

        return None, None, errs


#=============================================================================
class DefaultResourceHandler(ResourceHandler):
    def __init__(self, index_source, warc_paths='', forward_proxy_prefix=''):
        loaders = [WARCPathLoader(warc_paths, index_source),
                   LiveWebLoader(forward_proxy_prefix),
                   VideoLoader()
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


