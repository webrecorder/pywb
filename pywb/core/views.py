from pywb.utils.timeutils import timestamp_to_datetime
from pywb.framework.wbrequestresponse import WbResponse

import urlparse
import time

from os import path
from itertools import imap
from jinja2 import Environment, FileSystemLoader, PackageLoader


#=================================================================
class StaticTextView:
    def __init__(self, text):
        self.text = text

    def render_to_string(self, **kwargs):
        return self.text

    def render_response(self, **kwargs):
        return WbResponse.text_stream(self.text)

#=================================================================
class J2TemplateView:
    def __init__(self, filename):
        template_dir, template_file = path.split(filename)

        self.template_file = template_file

        self.jinja_env = self.make_jinja_env(template_dir)


    def make_jinja_env(self, template_dir):
        if template_dir.startswith('.') or template_dir.startswith('file://'):
            loader = FileSystemLoader(template_dir)
        else:
            loader = PackageLoader('pywb', template_dir)

        jinja_env = Environment(loader = loader, trim_blocks = True)
        jinja_env.filters['format_ts'] = J2TemplateView.format_ts
        jinja_env.filters['host'] = J2TemplateView.get_host
        jinja_env.filters['request_hostname'] = J2TemplateView.request_hostname
        return jinja_env

    def render_to_string(self, **kwargs):
        template = self.jinja_env.get_template(self.template_file)

        template_result = template.render(**kwargs)

        return template_result

    def render_response(self, **kwargs):
        template_result = self.render_to_string(**kwargs)
        status = kwargs.get('status', '200 OK')
        return WbResponse.text_response(str(template_result), status = status, content_type = 'text/html; charset=utf-8')


    # Filters
    @staticmethod
    def format_ts(value, format_='%a, %b %d %Y %H:%M:%S'):
        value = timestamp_to_datetime(value)
        return value.strftime(format_)

    @staticmethod
    def get_host(url):
        return urlparse.urlsplit(url).netloc


    @staticmethod
    def request_hostname(env):
        return env.get('HTTP_HOST', 'localhost')


# cdx index view

#=================================================================
# html captures 'calendar' view
#=================================================================
class J2HtmlCapturesView(J2TemplateView):
    def render_response(self, wbrequest, cdx_lines):
        return J2TemplateView.render_response(self,
                                    cdx_lines = list(cdx_lines),
                                    url = wbrequest.wb_url.url,
                                    prefix = wbrequest.wb_prefix)


#=================================================================
# stream raw cdx text
#=================================================================
class TextCapturesView:
    def render_response(self, wbrequest, cdx_lines):
        def to_str(cdx):
            cdx = str(cdx)
            if not cdx.endswith('\n'):
                cdx += '\n'
            return cdx
        cdx_lines = imap(to_str, cdx_lines)
        return WbResponse.text_stream(cdx_lines)



