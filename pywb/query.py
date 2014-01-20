import indexreader
import utils
import wbrequestresponse
import wbexceptions

from jinja2 import Environment, FileSystemLoader

class QueryHandler:
    def __init__(self, cdxserver = None):
        if not cdxserver:
            cdxserver = indexreader.RemoteCDXServer('http://web.archive.org/cdx/search/cdx')

        self.cdxserver = cdxserver

    def __call__(self, wbrequest):
        wburl = wbrequest.wb_url

        # init standard params
        params = self.cdxserver.getQueryParams(wburl)

        # add any custom filter from the request
        if wbrequest.queryFilter:
            params['filter'] = wbrequest.queryFilter

        if wbrequest.customParams:
            params.update(wbrequest.customParams)

        cdxlines = self.cdxserver.load(wburl.url, params)

        cdxlines = utils.peek_iter(cdxlines)

        if cdxlines is None:
            raise wbexceptions.NotFoundException('WB Does Not Have Url: ' + wburl.url)

        cdxlines = self.filterCdx(wbrequest, cdxlines)

        # Output raw cdx stream
        return wbrequestresponse.WbResponse.text_stream(cdxlines)

    def filterCdx(self, wbrequest, cdxlines):
        # Subclasses may wrap cdxlines iterator in a filter
        return cdxlines


class J2QueryRenderer:
    def __init__(self, template_dir, template_file):
        self.template_file = template_file

        self.jinja_env = Environment(loader = FileSystemLoader(template_dir), trim_blocks = True)

    def __call__(self, wbrequest, query_response):
        cdxlines = query_response.body

        def parse_cdx():
            for cdx in cdxlines:
                try:
                    cdx = indexreader.CDXCaptureResult(cdx)
                    yield cdx

                except wbexceptions.InvalidCDXException:
                    import traceback
                    traceback.print_exc()
                    pass


        template = self.jinja_env.get_template(self.template_file)
        response = template.render(cdxlines = parse_cdx(),
                                   url = wbrequest.wb_url.url,
                                   prefix = wbrequest.wb_prefix)

        return wbrequestresponse.WbResponse.text_response(str(response), content_type = 'text/html')


## ===========
## Simple handlers for debugging
class EchoEnv:
    def __call__(self, wbrequest):
        return wbrequestresponse.WbResponse.text_response(str(wbrequest.env))

class EchoRequest:
    def __call__(self, wbrequest):
        return wbrequestresponse.WbResponse.text_response(str(wbrequest))


