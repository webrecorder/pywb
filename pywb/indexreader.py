import urllib
import urllib2
import wbexceptions

from wbarchivalurl import ArchivalUrl

class RemoteCDXServer:
    """
    >>> x = cdxserver.load('example.com', parse_cdx = True, limit = '2')
    >>> pprint(vars(x[0]))
    {'digest': 'HT2DYGA5UKZCPBSFVCV3JOBXGW2G5UUA',
     'filename': 'DJ_crawl2.20020401123359-c/DJ_crawl3.20020120141301.arc.gz',
     'length': '1792',
     'mimetype': 'text/html',
     'offset': '49482198',
     'original': 'http://example.com:80/',
     'redirect': '-',
     'robotflags': '-',
     'statuscode': '200',
     'timestamp': '20020120142510',
     'urlkey': 'com,example)/'}

   """

    def __init__(self, serverUrl):
        self.serverUrl = serverUrl

    def load(self, url, params = {}, parse_cdx = False, **kwvalues):
        #url is required, must be passed explicitly!
        params['url'] = url
        params.update(**kwvalues)

        urlparams = urllib.urlencode(params)

        try:
            request = urllib2.Request(self.serverUrl, urlparams)
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

    @staticmethod
    def getQueryParams(wburl, limit = '150000', collapseTime = '10', replayClosest = '10'):
        return {

            ArchivalUrl.QUERY:
                {'collapseTime': collapseTime, 'filter': '!statuscode:(500|502|504)', 'limit': limit},

            ArchivalUrl.URL_QUERY:
                {'collapse': 'urlkey', 'matchType': 'prefix', 'showGroupCount': True, 'showUniqCount': True, 'lastSkipTimestamp': True, 'limit': limit,
                 'fl': 'urlkey,original,timestamp,endtimestamp,groupcount,uniqcount',
                },

            ArchivalUrl.REPLAY:
                {'sort': 'closest', 'filter': '!statuscode:(500|502|504)', 'limit': replayClosest, 'closest': wburl.timestamp, 'resolveRevisits': True},

            ArchivalUrl.LATEST_REPLAY:
                {'sort': 'reverse', 'filter': 'statuscode:[23]..', 'limit': '1', 'resolveRevisits': True}

        }[wburl.type]


class CDXCaptureResult:
    CDX_FORMATS = [["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","robotflags","length","offset","filename"],
                   ["urlkey","timestamp","original","mimetype","statuscode","digest","redirect","offset","filename"]]

    def __init__(self, cdxline):
        cdxline = cdxline.rstrip()
        fields = cdxline.split(' ')

        cdxformat = None
        for i in CDXCaptureResult.CDX_FORMATS:
            if len(i) == len(fields):
                cdxformat = i

        if not cdxformat:
            raise InvalidCDXException('unknown {0}-field cdx format'.format(len(fields)))

        for header, field in zip(cdxformat, fields):
            setattr(self, header, field)

    def __repr__(self):
        return str(vars(self))



# Testing


if __name__ == "__main__":
    import doctest
    from pprint import pprint

    cdxserver = RemoteCDXServer('http://web.archive.org/cdx/search/cdx')

    doctest.testmod()
