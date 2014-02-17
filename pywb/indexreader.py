import urllib
import urllib2
import wbexceptions

from itertools import chain
from pprint import pprint

from pywb.cdx.cdxserver import CDXServer, CDXException
from pywb.cdx.cdxobject import CDXObject

#=================================================================
class IndexReader(object):
    def __init__(self, config):
        if isinstance(config, str):
            self.cdx_server = CDXServer(config)
        else:
            self.cdx_server = CDXServer.create_from_config(config)

    def load_for_request(self, wbrequest):
        wburl = wbrequest.wb_url

        # init standard params
        params = self.get_query_params(wburl)

        # add any custom filter from the request
        if wbrequest.query_filter:
            params['filter'] = wbrequest.query_filter

        if wbrequest.custom_params:
            params.update(wbrequest.custom_params)

        params['url'] = wburl.url
        try:
            cdxlines = self.load_cdx(output='raw', **params)
        except CDXException:
            raise wbexceptions.BadUrlException('Bad Request Url: ' + wburl.url)

        cdxlines = self.peek_iter(cdxlines)

        if cdxlines is None:
            raise wbexceptions.NotFoundException('WB Does Not Have Url: ' + wburl.url)

        return cdxlines

    def load_cdx(self, **params):
        return self.cdx_server.load_cdx(**params)

    def get_query_params(self, wburl, limit = 150000, collapse_time = None, replay_closest = 10):
        if wburl.type == wburl.URL_QUERY:
            raise NotImplementedError('Url Query Not Yet Supported')

        return {
            wburl.QUERY:
                {'collapseTime': collapse_time, 'filter': '!statuscode:(500|502|504)', 'limit': limit},

            wburl.URL_QUERY:
                {'collapse': 'urlkey', 'matchType': 'prefix', 'showGroupCount': True, 'showUniqCount': True, 'lastSkipTimestamp': True, 'limit': limit,
                 'fl': 'urlkey,original,timestamp,endtimestamp,groupcount,uniqcount',
                },

            wburl.REPLAY:
                {'sort': 'closest', 'filter': '!statuscode:(500|502|504)', 'limit': replay_closest, 'closest': wburl.timestamp, 'resolveRevisits': True},

            # BUG: resolveRevisits currently doesn't work for this type of query
            # This is not an issue in archival mode, as there is a redirect to the actual timestamp query
            # but may be an issue in proxy mode
            wburl.LATEST_REPLAY:
                {'sort': 'reverse', 'filter': 'statuscode:[23]..', 'limit': '1', 'resolveRevisits': True}

        }[wburl.type]

    @staticmethod
    def peek_iter(iterable):
        try:
            first = next(iterable)
        except StopIteration:
            return None

        return chain([first], iterable)

#=================================================================
class RemoteCDXServer(IndexReader):
    def __init__(self, remote_url, cookie=None):
        self.remote = RemoteCDXSource(remote_url=remote_url, cookie=cookie, proxy_all=True)
        self.cdx_server = CDXServer(self.remote)

    #def load_cdx(self, **params):
        #return remote.load_cdx(**params)
