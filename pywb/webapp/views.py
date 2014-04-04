from pywb.utils.timeutils import timestamp_to_datetime
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.memento import make_timemap, LINK_FORMAT

from handlers import WBHandler

import urlparse
import logging

from os import path
from itertools import imap
from jinja2 import Environment, FileSystemLoader, PackageLoader


FILTERS = {}


#=================================================================
class template_filter(object):
    """
    Decorator for registering a function as a jinja2 filter
    If optional argument is supplied, it is used as the filter name
    Otherwise, the func name is the filter name
    """
    def __init__(self, param=None):
        if hasattr(param, '__call__'):
            self.name = None
            self.__call__(param)
        else:
            self.name = param

    def __call__(self, func):
        name = self.name
        if not name:
            name = func.__name__

        FILTERS[name] = func
        return func


#=================================================================
# Filters
@template_filter
def format_ts(value, format_='%a, %b %d %Y %H:%M:%S'):
    value = timestamp_to_datetime(value)
    return value.strftime(format_)


@template_filter('host')
def get_hostname(url):
    return urlparse.urlsplit(url).netloc


@template_filter()
def request_hostname(env):
    return env.get('HTTP_HOST', 'localhost')


@template_filter()
def is_wb_handler(obj):
    if not hasattr(obj, 'handler'):
        return False

    return isinstance(obj.handler, WBHandler)


#=================================================================
class J2TemplateView:
    env_globals = {}

    def __init__(self, filename):
        template_dir, template_file = path.split(filename)

        self.template_file = template_file

        self.jinja_env = self.make_jinja_env(template_dir)

    def make_jinja_env(self, template_dir):
        if template_dir.startswith('.') or template_dir.startswith('file://'):
            loader = FileSystemLoader(template_dir)
        else:
            loader = PackageLoader('pywb', template_dir)

        jinja_env = Environment(loader=loader, trim_blocks=True)
        jinja_env.filters.update(FILTERS)
        jinja_env.globals.update(self.env_globals)
        return jinja_env

    def render_to_string(self, **kwargs):
        template = self.jinja_env.get_template(self.template_file)

        template_result = template.render(**kwargs)

        return template_result

    def render_response(self, **kwargs):
        template_result = self.render_to_string(**kwargs)
        status = kwargs.get('status', '200 OK')
        content_type = 'text/html; charset=utf-8'
        return WbResponse.text_response(str(template_result),
                                        status=status,
                                        content_type=content_type)


#=================================================================
def add_env_globals(glb):
    J2TemplateView.env_globals.update(glb)


#=================================================================
def load_template_file(file, desc=None, view_class=J2TemplateView):
    if file:
        logging.debug('Adding {0}: {1}'.format(desc if desc else name, file))
        file = view_class(file)

    return file


#=================================================================
def load_query_template(file, desc=None):
    return load_template_file(file, desc, J2HtmlCapturesView)


#=================================================================
# query views
#=================================================================
class J2HtmlCapturesView(J2TemplateView):
    def render_response(self, wbrequest, cdx_lines):
        return J2TemplateView.render_response(self,
                                    cdx_lines=list(cdx_lines),
                                    url=wbrequest.wb_url.url,
                                    type=wbrequest.wb_url.type,
                                    prefix=wbrequest.wb_prefix)


#=================================================================
class MementoTimemapView(object):
    def render_response(self, wbrequest, cdx_lines):
        memento_lines = make_timemap(wbrequest, cdx_lines)
        return WbResponse.text_stream(memento_lines,
                                      content_type=LINK_FORMAT)
