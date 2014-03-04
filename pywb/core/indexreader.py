import urllib
import urllib2


#=================================================================
class IndexReader(object):
    """
    Main interface for reading index (currently only CDX) from a
    source server (currently a cdx server)

    Creates an appropriate query based on wbrequest type info
    """

    def __init__(self, cdx_server, perms_policy):
        self.cdx_server = cdx_server
        self.perms_policy = perms_policy

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
        params['output'] = 'cdxobject'
        params['url'] = wburl.url

        cdxlines = self.load_cdx(wbrequest, params)

        return cdxlines

    def load_cdx(self, wbrequest, params):
        if self.perms_policy:
            perms_op = self.perms_policy.create_perms_filter_op(wbrequest)
            if perms_op:
                params['custom_ops'] = [perms_op]

        return self.cdx_server.load_cdx(**params)

    def cdx_load_callback(self, wbrequest):
        def load_cdx(params):
            return self.load_cdx(wbrequest, params)
        return load_cdx

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

            wburl.LATEST_REPLAY:
                {'sort': 'reverse', 'filter': ['statuscode:[23]..'], 'limit': '1', 'resolveRevisits': True}

        }[wburl.type]
