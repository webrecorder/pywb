import urllib
import urllib2

from pywb.cdx.cdxserver import create_cdx_server

#=================================================================
class IndexReader(object):
    """
    Main interface for reading index (currently only CDX) from a
    source server (currenlt a cdx server)

    Creates an appropriate query based on wbrequest type info
    """

    def __init__(self, config, ds_rules_file=None):
        self.cdx_server = create_cdx_server(config, ds_rules_file)

    def load_for_request(self, wbrequest):
        wburl = wbrequest.wb_url

        # init standard params
        params = self.get_query_params(wburl)

        # add any custom filter from the request
        if wbrequest.query_filter:
            params['filter'].extend(wbrequest.query_filter)

        if wbrequest.custom_params:
            params.update(wbrequest.custom_params)

        params['allowFuzzy'] = True

        cdxlines = self.load_cdx(url=wburl.url, output='raw', **params)

        return cdxlines

    def load_cdx(self, **params):
        return self.cdx_server.load_cdx(**params)

    def get_query_params(self, wburl, limit = 150000, collapse_time = None, replay_closest = 100):
        if wburl.type == wburl.URL_QUERY:
            raise NotImplementedError('Url Query Not Yet Supported')

        return {
            wburl.QUERY:
                {'collapseTime': collapse_time, 'filter': ['!statuscode:(500|502|504)'], 'limit': limit},

            wburl.URL_QUERY:
                {'collapse': 'urlkey', 'matchType': 'prefix', 'showGroupCount': True, 'showUniqCount': True, 'lastSkipTimestamp': True, 'limit': limit,
                 'fl': 'urlkey,original,timestamp,endtimestamp,groupcount,uniqcount',
                },

            wburl.REPLAY:
                {'sort': 'closest', 'filter': ['!statuscode:(500|502|504)'], 'limit': replay_closest, 'closest': wburl.timestamp, 'resolveRevisits': True},

            # BUG: resolveRevisits currently doesn't work for this type of query
            # This is not an issue in archival mode, as there is a redirect to the actual timestamp query
            # but may be an issue in proxy mode
            wburl.LATEST_REPLAY:
                {'sort': 'reverse', 'filter': ['statuscode:[23]..'], 'limit': '1', 'resolveRevisits': True}

        }[wburl.type]
