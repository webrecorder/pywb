from pywb.utils.timeutils import timestamp_to_datetime, timestamp_to_sec
from pywb.framework.wbrequestresponse import WbResponse
from pywb.framework.memento import make_timemap, LINK_FORMAT

import urlparse
import urllib
import logging
import json

from os import path
from itertools import imap
from jinja2 import Environment
from jinja2 import FileSystemLoader, PackageLoader, ChoiceLoader


FILTERS = {}


#=================================================================
class template_filter(object):
    """
    Decorator for registering a function as a jinja2 filter
    If optional argument is supplied, it is used as the filter name
    Otherwise, the func name is the filter name
    """
    def __init__(self, param=None):
        self.name = param

    def __call__(self, func):
        name = self.name
        if not name:
            name = func.__name__

        FILTERS[name] = func
        return func


#=================================================================
# Filters
@template_filter()
def format_ts(value, format_='%a, %b %d %Y %H:%M:%S'):
    if format_ == '%s':
        return timestamp_to_sec(value)
    else:
        value = timestamp_to_datetime(value)
        return value.strftime(format_)


@template_filter('urlsplit')
def get_urlsplit(url):
    split = urlparse.urlsplit(url)
    return split


@template_filter()
def is_wb_handler(obj):
    if not hasattr(obj, 'handler'):
        return False

    return obj.handler.__class__.__name__ == "WBHandler"


@template_filter()
def tojson(obj):
    return json.dumps(obj)


#=================================================================
class J2TemplateView(object):
    env_globals = {'static_path': 'static/__pywb',
                   'packages': ['pywb']}

    def __init__(self, filename):
        template_dir, template_file = path.split(filename)
        self.template_file = template_file

        self.jinja_env = self.make_jinja_env(template_dir)

    def make_jinja_env(self, template_dir):
        loaders = self._make_loaders(template_dir)
        loader = ChoiceLoader(loaders)

        jinja_env = Environment(loader=loader, trim_blocks=True)
        jinja_env.filters.update(FILTERS)
        jinja_env.globals.update(self.env_globals)
        return jinja_env

    def _make_loaders(self, template_dir):
        loaders = []
        loaders.append(FileSystemLoader(template_dir))
        # add relative and absolute path loaders for banner support
        loaders.append(FileSystemLoader('.'))
        loaders.append(FileSystemLoader('/'))

        # add loaders for all specified packages
        for package in self.env_globals['packages']:
            loaders.append(PackageLoader(package,
                                         template_dir))
        return loaders

    def render_to_string(self, **kwargs):
        template = self.jinja_env.get_template(self.template_file)

        template_result = template.render(**kwargs)

        return template_result

    def render_response(self, **kwargs):
        template_result = self.render_to_string(**kwargs)
        status = kwargs.get('status', '200 OK')
        content_type = kwargs.get('content_type', 'text/html; charset=utf-8')
        return WbResponse.text_response(template_result.encode('utf-8'),
                                        status=status,
                                        content_type=content_type)

    @staticmethod
    def create_template(filename, desc='', view_class=None):
        if not filename:
            return None

        if not view_class:
            view_class = J2TemplateView

        logging.debug('Adding {0}: {1}'.format(desc, filename))
        return view_class(filename)


#=================================================================
def add_env_globals(glb):
    J2TemplateView.env_globals.update(glb)


#=================================================================
class HeadInsertView(J2TemplateView):
    def create_insert_func(self, wbrequest,
                           include_ts=True):

        url = wbrequest.wb_url.get_url()

        top_url = wbrequest.wb_prefix
        top_url += wbrequest.wb_url.to_str(mod=wbrequest.final_mod)

        include_wombat = not wbrequest.wb_url.is_banner_only

        def make_head_insert(rule, cdx):
            cdx['url'] = url
            return (self.render_to_string(wbrequest=wbrequest,
                                          cdx=cdx,
                                          top_url=top_url,
                                          include_ts=include_ts,
                                          include_wombat=include_wombat,
                                          banner_html=self.banner_html,
                                          rule=rule))
        return make_head_insert

    @staticmethod
    def init_from_config(config):
        view = config.get('head_insert_view')
        if not view:
            html = config.get('head_insert_html', 'templates/head_insert.html')

            if html:
                banner_html = config.get('banner_html', 'banner.html')
                view = HeadInsertView(html)
                logging.debug('Adding HeadInsert: {0}, Banner {1}'.
                              format(html, banner_html))

                view.banner_html = banner_html

        return view


#=================================================================
# query views
#=================================================================
class J2HtmlCapturesView(J2TemplateView):
    def render_response(self, wbrequest, cdx_lines, **kwargs):
        def format_cdx_lines():
            for cdx in cdx_lines:
                cdx['_orig_url'] = cdx['url']
                cdx['url'] = wbrequest.wb_url.get_url(url=cdx['url'])
                yield cdx

        return J2TemplateView.render_response(self,
                                    cdx_lines=list(format_cdx_lines()),
                                    url=wbrequest.wb_url.get_url(),
                                    type=wbrequest.wb_url.type,
                                    prefix=wbrequest.wb_prefix,
                                    **kwargs)

    @staticmethod
    def create_template(filename, desc=''):
        return J2TemplateView.create_template(filename, desc,
                                              J2HtmlCapturesView)


#=================================================================
class MementoTimemapView(object):
    def render_response(self, wbrequest, cdx_lines, **kwargs):
        memento_lines = make_timemap(wbrequest, cdx_lines)
        return WbResponse.text_stream(memento_lines,
                                      content_type=LINK_FORMAT)
