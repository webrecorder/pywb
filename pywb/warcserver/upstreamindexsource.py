from warcio.timeutils import timestamp_now

from pywb.utils.wbexception import NotFoundException

from pywb.warcserver.index.cdxobject import CDXObject
from pywb.warcserver.index.indexsource import BaseIndexSource, RemoteIndexSource
from pywb.warcserver.resource.responseloader import LiveWebLoader
from pywb.utils.format import ParamFormatter, res_template


#=============================================================================
class UpstreamAggIndexSource(RemoteIndexSource):
    def __init__(self, base_url):
        api_url = base_url + '/index?url={url}'
        proxy_url = base_url + '/resource?url={url}&closest={timestamp}'
        super(UpstreamAggIndexSource, self).__init__(api_url, proxy_url, 'filename')

    def _set_load_url(self, cdx, params):
        super(UpstreamAggIndexSource, self)._set_load_url(cdx, params)
        cdx['offset'] = '0'
        cdx.pop('load_url', '')


#=============================================================================
class UpstreamMementoIndexSource(BaseIndexSource):
    def __init__(self, proxy_url='{url}'):
        self.proxy_url = proxy_url
        self.loader = LiveWebLoader()

    def load_index(self, params):
        cdx = CDXObject()
        cdx['urlkey'] = params.get('key').decode('utf-8')

        closest = params.get('closest')
        cdx['timestamp'] = closest if closest else timestamp_now()
        cdx['url'] = params['url']
        cdx['load_url'] = res_template(self.proxy_url, params)
        cdx['memento_url'] = cdx['load_url']
        return self._do_load(cdx, params)

    def _do_load(self, cdx, params):
        result = self.loader.load_resource(cdx, params)
        if not result:
            raise NotFoundException('Not a memento: ' + cdx['url'])

        cdx['_cached_result'] = result
        yield cdx

    def __str__(self):
        return 'upstream'

    @staticmethod
    def upstream_resource(base_url):
        return UpstreamMementoIndexSource(base_url + '/resource?url={url}&closest={closest}')


