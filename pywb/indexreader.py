import urllib
import urllib2
import wbexceptions
import itertools
from collections import OrderedDict

from wbarchivalurl import ArchivalUrl

class RemoteCDXServer:
    """
    >>> x = cdxserver.load('example.com', parse_cdx = True, limit = '2')
    >>> pprint(x[0])
    {'digest': 'HT2DYGA5UKZCPBSFVCV3JOBXGW2G5UUA',
     'length': '1792',
     'mimetype': 'text/html',
     'original': 'http://example.com:80/',
     'statuscode': '200',
     'timestamp': '20020120142510',
     'urlkey': 'com,example)/'}

     """

    def __init__(self, serverUrl, cookie = None):
        self.serverUrl = serverUrl
        self.authCookie = cookie

    def load(self, url, params = {}, parse_cdx = False, **kwvalues):
        #url is required, must be passed explicitly!
        params['url'] = url
        params.update(**kwvalues)

        urlparams = urllib.urlencode(params, True)

        try:
            request = urllib2.Request(self.serverUrl, urlparams)

            if self.authCookie:
                request.add_header('Cookie', self.authCookie)

            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            if e.code == 403:
                exc_msg = e.read()
                msg = 'Blocked By Robots' if 'Blocked By Robots' in exc_msg else 'Excluded'
                raise wbexceptions.AccessException(msg)
            else:
                raise e

        if parse_cdx:
            return map(CDXCaptureResult, response)
        else:
            return response

    # BUG: Setting replayClosest to high number for now, as cdx server sometimes returns wrong result
    # with lower values if there are too many captures. Ideally, should be around 10-20
    # The replayClosest is the max number of cdx lines, so max number of retry attempts that WB will make

    @staticmethod
    def getQueryParams(wburl, limit = '150000', collapseTime = '10', replayClosest = '4000'):
        return {

            wburl.QUERY:
                {'collapseTime': collapseTime, 'filter': '!statuscode:(500|502|504)', 'limit': limit},

            wburl.URL_QUERY:
                {'collapse': 'urlkey', 'matchType': 'prefix', 'showGroupCount': True, 'showUniqCount': True, 'lastSkipTimestamp': True, 'limit': limit,
                 'fl': 'urlkey,original,timestamp,endtimestamp,groupcount,uniqcount',
                },

            wburl.REPLAY:
                {'sort': 'closest', 'filter': '!statuscode:(500|502|504)', 'limit': replayClosest, 'closest': wburl.timestamp, 'resolveRevisits': True},

            # BUG: resolveRevisits currently doesn't work for this type of query
            # This is not an issue in archival mode, as there is a redirect to the actual timestamp query
            # but may be an issue in proxy mode
            wburl.LATEST_REPLAY:
                {'sort': 'reverse', 'filter': 'statuscode:[23]..', 'limit': '1', 'resolveRevisits': True}

        }[wburl.type]


class CDXCaptureResult(OrderedDict):
    CDX_FORMATS = [
        # Public CDX Format
        ["urlkey","timestamp","original","mimetype","statuscode","digest","length"],

        # CDX 11 Format
        ["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","robotflags","length","offset","filename"],

        # CDX 9 Format
        ["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","offset","filename"],

        # CDX 11 Format + 3 revisit resolve fields
        ["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","robotflags","length","offset","filename",
         "orig.length","orig.offset","orig.filename"],

        # CDX 9 Format + 3 revisit resolve fields
        ["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","offset","filename",
         "orig.length","orig.offset","orig.filename"]
        ]

    def __init__(self, cdxline):
        OrderedDict.__init__(self)

        cdxline = cdxline.rstrip()
        fields = cdxline.split(' ')

        cdxformat = None
        for i in CDXCaptureResult.CDX_FORMATS:
            if len(i) == len(fields):
                cdxformat = i

        if not cdxformat:
            raise wbexceptions.InvalidCDXException('unknown {0}-field cdx format'.format(len(fields)))

        for header, field in itertools.izip(cdxformat, fields):
            self[header] = field
    #        setattr(self, header, field)

    #def __repr__(self):
    #    return str(vars(self))



# Testing


if __name__ == "__main__":
    import doctest
    from pprint import pprint

    cdxserver = RemoteCDXServer('http://web.archive.org/cdx/search/cdx')

    doctest.testmod()
