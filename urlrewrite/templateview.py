from pywb.utils.timeutils import timestamp_to_datetime, timestamp_to_sec
from pywb.utils.timeutils import timestamp_now
from six.moves.urllib.parse import urlsplit

from jinja2 import Environment
from jinja2 import FileSystemLoader, PackageLoader, ChoiceLoader

import json
import os


# ============================================================================
class FileOnlyPackageLoader(PackageLoader):
    def get_source(self, env, template):
        dir_, file_ = os.path.split(template)
        return super(FileOnlyPackageLoader, self).get_source(env, file_)


# ============================================================================
class RelEnvironment(Environment):
    """Override join_path() to enable relative template paths."""
    def join_path(self, template, parent):
        return os.path.join(os.path.dirname(parent), template)


# ============================================================================
class JinjaEnv(object):
    def __init__(self, paths=['templates', '.', '/'],
                       packages=['pywb'],
                       globals=None,
                       overlay=None):

        self._init_filters()

        loader = ChoiceLoader(self._make_loaders(paths, packages))

        if overlay:
            jinja_env = overlay.jinja_env.overlay(loader=loader, trim_blocks=True)
        else:
            jinja_env = RelEnvironment(loader=loader, trim_blocks=True)

        jinja_env.filters.update(self.filters)
        if globals:
            jinja_env.globals.update(globals)
        self.jinja_env = jinja_env

    def _make_loaders(self, paths, packages):
        loaders = []
        # add loaders for paths
        for path in paths:
            loaders.append(FileSystemLoader(path))

        # add loaders for all specified packages
        for package in packages:
            loaders.append(FileOnlyPackageLoader(package))

        return loaders

    def template_filter(self, param=None):
        def deco(func):
            name = param or func.__name__
            self.filters[name] = func
            return func

        return deco

    def _init_filters(self):
        self.filters = {}

        @self.template_filter()
        def format_ts(value, format_='%a, %b %d %Y %H:%M:%S'):
            if format_ == '%s':
                return timestamp_to_sec(value)
            else:
                value = timestamp_to_datetime(value)
                return value.strftime(format_)

        @self.template_filter('urlsplit')
        def get_urlsplit(url):
            split = urlsplit(url)
            return split

        @self.template_filter()
        def tojson(obj):
            return json.dumps(obj)


# ============================================================================
class BaseInsertView(object):
    def __init__(self, jenv, insert_file, banner_file):
        self.jenv = jenv
        self.insert_file = insert_file
        self.banner_file = banner_file

    def render_to_string(self, env, **kwargs):
        template = self.jenv.jinja_env.get_template(self.insert_file)
        params = env.get('webrec.template_params')
        if params:
            kwargs.update(params)

        return template.render(**kwargs)


# ============================================================================
class HeadInsertView(BaseInsertView):
    def create_insert_func(self, wb_url,
                           wb_prefix,
                           host_prefix,
                           env,
                           is_framed,
                           coll='',
                           include_ts=True):

        url = wb_url.get_url()

        top_url = wb_prefix
        top_url += wb_url.to_str(mod='')

        include_wombat = not wb_url.is_banner_only

        wbrequest = {'host_prefix': host_prefix,
                     'wb_prefix': wb_prefix,
                     'wb_url': wb_url,
                     'coll': coll,
                     'env': env,
                     'options': {'is_framed': is_framed},
                     'rewrite_opts': {}
                    }

        def make_head_insert(rule, cdx):
            return (self.render_to_string(env, wbrequest=wbrequest,
                                          cdx=cdx,
                                          top_url=top_url,
                                          include_ts=include_ts,
                                          include_wombat=include_wombat,
                                          banner_html=self.banner_file,
                                          rule=rule))
        return make_head_insert


# ============================================================================
class TopFrameView(BaseInsertView):
    def get_top_frame(self, wb_url,
                      wb_prefix,
                      host_prefix,
                      env,
                      frame_mod,
                      replay_mod,
                      coll='',
                      extra_params=None):

        embed_url = wb_url.to_str(mod=replay_mod)

        if wb_url.timestamp:
            timestamp = wb_url.timestamp
        else:
            timestamp = timestamp_now()

        wbrequest = {'host_prefix': host_prefix,
                     'wb_prefix': wb_prefix,
                     'wb_url': wb_url,
                     'coll': coll,

                     'options': {'frame_mod': frame_mod,
                                 'replay_mod': replay_mod},
                    }

        params = dict(embed_url=embed_url,
                      wbrequest=wbrequest,
                      timestamp=timestamp,
                      url=wb_url.get_url(),
                      banner_html=self.banner_file)

        if extra_params:
            params.update(extra_params)

        return self.render_to_string(env, **params)


