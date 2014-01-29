import indexreader
import utils
import wbrequestresponse
import wbexceptions

from itertools import imap
from jinja2 import Environment, FileSystemLoader


#=================================================================
class TextQueryView:
    def __call__(self, wbrequest, cdx_lines):
        cdx_lines = imap(lambda x: str(x) + '\n', cdx_lines)
        return wbrequestresponse.WbResponse.text_stream(cdx_lines)

#=================================================================
class J2QueryView:
    def __init__(self, template_dir, template_file, buffer_index = True):
        self.template_file = template_file
        self.buffer_index = buffer_index

        self.jinja_env = Environment(loader = FileSystemLoader(template_dir), trim_blocks = True)


    def __call__(self, wbrequest, cdx_lines):
        template = self.jinja_env.get_template(self.template_file)

        # buffer/convert to list so we have length available for template
        if self.buffer_index:
            cdx_lines = list(cdx_lines)

        response = template.render(cdx_lines = cdx_lines,
                                   url = wbrequest.wb_url.url,
                                   prefix = wbrequest.wb_prefix)

        return wbrequestresponse.WbResponse.text_response(str(response), content_type = 'text/html')


#=================================================================
class DebugEchoView:
    def __call__(self, wbrequest):
        return wbrequestresponse.WbResponse.text_response(str(wbrequest.env))

#=================================================================
class DebugEchoView:
    def __call__(self, wbrequest):
        return wbrequestresponse.WbResponse.text_response(str(wbrequest))


