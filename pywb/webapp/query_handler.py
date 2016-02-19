from pywb.utils.dsrules import DEFAULT_RULES_FILE

from pywb.perms.perms_filter import make_perms_cdx_filter
from pywb.framework.wbrequestresponse import WbResponse
from pywb.cdx.cdxserver import create_cdx_server
from pywb.webapp.views import MementoTimemapView


#=================================================================
class QueryHandler(object):
    """
    Main interface for querying the index (currently only CDX) from a
    source server (currently a cdx server)

    Creates an appropriate query based on wbrequest type info and outputs
    a returns a view for the cdx, either a raw cdx iter, an html view,
    etc...
    """

    def __init__(self, cdx_server, html_query_view=None, perms_policy=None):
        self.cdx_server = cdx_server
        self.perms_policy = perms_policy

        self.views = {}
        if html_query_view:
            self.views['html'] = html_query_view

        self.views['timemap'] = MementoTimemapView()

    @staticmethod
    def init_from_config(config,
                         ds_rules_file=DEFAULT_RULES_FILE,
                         html_view=None,
                         server_cls=None):

        perms_policy = None

        if hasattr(config, 'get'):
            perms_policy = config.get('perms_policy')
            server_cls = config.get('server_cls', server_cls)

        cdx_server = create_cdx_server(config, ds_rules_file, server_cls)

        return QueryHandler(cdx_server, html_view, perms_policy)

    def get_output_type(self, wb_url):
        # cdx server only supports text and cdxobject for now
        if wb_url.mod == 'cdx_':
            output = 'text'
        elif wb_url.mod == 'timemap':
            output = 'timemap'
        elif wb_url.is_query():
            output = 'html'
        else:
            output = 'cdxobject'

        return output

    def load_for_request(self, wbrequest):
        wbrequest.normalize_post_query()

        wb_url = wbrequest.wb_url
        output = self.get_output_type(wb_url)

        # init standard params
        params = self.get_query_params(wb_url)

        params['allowFuzzy'] = True
        params['url'] = wb_url.url
        params['output'] = output

        params['filter'].append('!mimetype:-')

        # get metadata
        if wb_url.mod == 'vi_':
            # matching metadata explicitly with special scheme
            schema, rest = wb_url.url.split('://', 1)
            params['url'] = 'metadata://' + rest
            params['filter'].append('~original:metadata://')

        cdx_iter = self.load_cdx(wbrequest, params)
        return cdx_iter, output

    def load_cdx(self, wbrequest, params):
        if wbrequest:
            # add any custom filter from the request
            if wbrequest.query_filter:
                filters = params.get('filter')
                if filters:
                    filters.extend(wbrequest.query_filter)
                else:
                    params['filter'] = wbrequest.query_filter

            params['coll'] = wbrequest.coll
            if wbrequest.custom_params:
                params.update(wbrequest.custom_params)

        if self.perms_policy:
            perms_op = make_perms_cdx_filter(self.perms_policy, wbrequest)
            if perms_op:
                params['custom_ops'] = [perms_op]

        cdx_iter = self.cdx_server.load_cdx(**params)
        return cdx_iter

    def make_cdx_response(self, wbrequest, cdx_iter, output, **kwargs):
        # if not text, the iterator is assumed to be CDXObjects
        if output and output != 'text':
            view = self.views.get(output)
            if view:
                return view.render_response(wbrequest, cdx_iter, **kwargs)

        return WbResponse.text_stream(cdx_iter)

    def cdx_load_callback(self, wbrequest):
        def load_cdx(params):
            params['output'] = 'cdxobject'
            return self.load_cdx(wbrequest, params)

        return load_cdx

    def get_query_params(self,
                         wburl, limit=150000,
                         collapse_time=None,
                         replay_closest=100):

        #if wburl.type == wburl.URL_QUERY:
        #    raise NotImplementedError('Url Query Not Yet Supported')

        return {
            wburl.QUERY:
                {'collapseTime': collapse_time,
                 'filter': ['!statuscode:(500|502|504)'],
                 'from': wburl.timestamp,
                 'to': wburl.end_timestamp,
                 'limit': limit,
                 'matchType': 'exact',
                },

            wburl.URL_QUERY:
                {'collapse': 'urlkey',
                 'matchType': 'prefix',
                 'showGroupCount': True,
                 'showUniqCount': True,
                 'lastSkipTimestamp': True,
                 'limit': limit,
                 'fl': ('urlkey,original,timestamp,' +
                        'endtimestamp,groupcount,uniqcount'),
                 'filter': [],
                },

            wburl.REPLAY:
                {'sort': 'closest',
                 'filter': ['!statuscode:(500|502|504)'],
                 'limit': replay_closest,
                 'closest': wburl.timestamp,
                 'resolveRevisits': True,
                 'matchType': 'exact',
                },

            wburl.LATEST_REPLAY:
                {'sort': 'reverse',
       # Not appropriate as default
       # Should be an option to configure status code filtering in general
       #         'filter': ['statuscode:[23]..|-'],
                 'filter': [],
                 'limit': '1',
                 'resolveRevisits': True,
                 'matchType': 'exact',
                }

        }[wburl.type]
