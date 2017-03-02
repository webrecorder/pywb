from pywb.cdx.cdxobject import CDXObject
from pywb.utils.wbexception import NotFoundException
from pywb.webagg.indexsource import BaseIndexSource, RemoteIndexSource
from pywb.webagg.responseloader import LiveWebLoader
from pywb.webagg.utils import ParamFormatter, res_template
from warcio.timeutils import timestamp_now


#=============================================================================
class UpstreamAggIndexSource(RemoteIndexSource):
    def __init__(self, base_url):
        api_url = base_url + '/index?url={url}'
        proxy_url = base_url + '/resource?url={url}&closest={timestamp}'
        super(UpstreamAggIndexSource, self).__init__(api_url, proxy_url, 'filename')

    def _set_load_url(self, cdx):
        super(UpstreamAggIndexSource, self)._set_load_url(cdx)
        cdx['offset'] = '0'
        cdx.pop('load_url', '')


#=============================================================================
class ProxyMementoIndexSource(BaseIndexSource):
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
        return 'proxy'

    @staticmethod
    def upstream_resource(base_url):
        return ProxyMementoIndexSource(base_url + '/resource?url={url}&closest={closest}')


