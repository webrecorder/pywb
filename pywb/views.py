import indexreader
import utils
import wbrequestresponse
import wbexceptions
import time

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

        self.jinja_env = make_jinja_env(template_dir)


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
# Render the head insert (eg. banner)
#=================================================================
class J2HeadInsertView:
    def __init__(self, template_dir, template_file, buffer_index = True):
        self.template_file = template_file

        self.jinja_env = make_jinja_env(template_dir)


    def __call__(self, wbrequest, cdx):
        template = self.jinja_env.get_template(self.template_file)


        return template.render(wbrequest = wbrequest,cdx = cdx)



#=================================================================
# Jinja funcs
def make_jinja_env(template_dir):
    jinja_env = Environment(loader = FileSystemLoader(template_dir), trim_blocks = True)
    jinja_env.filters['format_ts'] = format_ts
    return jinja_env

# Filters
def format_ts(value, format='%H:%M / %d-%m-%Y'):
    value = utils.timestamp_to_datetime(value)
    return time.strftime(format, value)
