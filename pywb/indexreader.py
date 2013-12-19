import urllib
import urllib2

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
        request = urllib2.Request(self.serverUrl, urlparams)
        response = urllib2.urlopen(request)

        if parse_cdx:
            return map(CDXCaptureResult, response)
        else:
            return response

class InvalidCDXException(Exception):
    pass

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
            raise InvalidCDXException('unknown %d-field cdx format' % len(fields))

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
