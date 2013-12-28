import indexreader
from wbrequestresponse import WbResponse
import utils

class ReplayHandler:
    def __init__(self, resolvers, archiveloader):
        self.resolvers = resolvers
        self.archiveloader = archiveloader

    def __call__(self, wbrequest, query_response):
        cdxlist = query_response.body
        last_e = None
        first = True
        for cdx in cdxlist:
            try:
                cdx = indexreader.CDXCaptureResult(cdx)

                # First time through, check if do redirect before warc load
                if first and (cdx['timestamp'] != wbrequest.wb_url.timestamp):
                    return WbResponse.better_timestamp_response(wbrequest, cdx['timestamp'])

                response = self.doReplay(cdx, wbrequest)

                if response:
                    # if a fallback, redirect to exact timestamp!
                    if not first and (cdx['timestamp'] != wbrequest.wb_url.timestamp):
                        response.close()
                        return WbResponse.better_timestamp_response(wbrequest, cdx['timestamp'])

                    return response

                first = False

            except Exception, e:
                import traceback
                traceback.print_exc()
                last_e = e
                pass

        if last_e:
            raise last_e

    def _load(self, cdx, revisit = False):
        prefix = '' if not revisit else 'orig.'
        return self.archiveloader.load(self.resolveFull(cdx[prefix + 'filename']), cdx[prefix + 'offset'], cdx[prefix + 'length'])

    def doReplay(self, cdx, wbrequest):
        hasCurr = (cdx['filename'] != '-')
        hasOrig = (cdx['orig.filename'] != '-')

        # Case 1: non-revisit
        if (hasCurr and not hasOrig):
            headersRecord = self._load(cdx, False)
            payloadRecord = headersRecord
            isRevisit = False

        # Case 2: old-style revisit, load headers from original payload
        elif (not hasCurr and hasOrig):
            payloadRecord = self._load(cdx, False)
            headersRecord = payloadRecord
            isRevisit = True

        # Case 3: modern revisit, load headers from curr, payload from original
        elif (hasCurr and hasOrig):
            headersRecord = self._load(cdx, False)
            payloadRecord = self._load(cdx, True)

            # Case 4: if headers record is actually empty (eg empty revisit), then use headers from revisit
            if not headersRecord.httpHeaders:
                headersRecord.close()
                headersRecord = payloadRecord

            isRevisit = True

        else:
            raise wbexceptions.CaptureException('Invalid CDX' + cdx)

        # Check for self redirect
        if headersRecord.statusline.startswith('3'):
            if self.isSelfRedirect(wbrequest, headersRecord):
                raise wbexception.CaptureException('Self Redirect: ' + cdx)

        return WbResponse.stream_response(headersRecord.statusline, headersRecord.httpHeaders, payloadRecord.stream)

    def isSelfRedirect(self, wbrequest, record):
        requestUrl = wbrequest.wb_url.url.lower()
        locationUrl = utils.get_header(record.httpHeaders, 'Location').lower()
        return requestUrl == locationUrl
        #ArchivalUrlRewriter.stripProtocol(requestUrl) == ArchivalUrlRewriter.stripProtocol(locationUrl)


    def resolveFull(self, filename):
        # Attempt to resolve cdx file to full path
        fullUrl = None
        for resolver in self.resolvers:
            fullUrl = resolver(filename)
            if fullUrl:
                return fullUrl

        raise exceptions.UnresolvedArchiveFileException('Archive File Not Found: ' + cdx.filename)


#======================================
# PrefixResolver - convert cdx file entry to url with prefix if url contains specified string
#======================================
def PrefixResolver(prefix, contains):
    def makeUrl(url):
        return prefix + url if (contains in url) else None

    return makeUrl
