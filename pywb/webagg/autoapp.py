from pywb.webagg.app import ResAggApp
from pywb.webagg.utils import load_config
from pywb.utils.loaders import load_yaml_config

from pywb.webagg.aggregator import CacheDirectoryIndexSource, GeventTimeoutAggregator, SimpleAggregator
from pywb.webagg.handlers import DefaultResourceHandler, HandlerSeq
from pywb.webagg.indexsource import FileIndexSource, RemoteIndexSource, MementoIndexSource, RedisIndexSource
from pywb.webagg.indexsource import LiveIndexSource

from pywb import DEFAULT_CONFIG

from six import iteritems, iterkeys, itervalues
from six.moves import zip
import os


SOURCE_LIST = [LiveIndexSource,
               RedisIndexSource,
               MementoIndexSource,
               CacheDirectoryIndexSource,
               FileIndexSource,
               RemoteIndexSource
              ]


# ============================================================================
class AutoConfigApp(ResAggApp):
    def __init__(self, config_file='./config.yaml'):
        config = load_yaml_config(DEFAULT_CONFIG)

        try:
            new_config = load_config('PYWB_CONFIG_FILE', config_file)
        except Exception as e:
            new_config = {}
            print(e)

        if new_config:
            config.update(new_config)

        super(AutoConfigApp, self).__init__(debug=config.get('debug', False))
        self.config = config

    def init(self):
        if self.config.get('enable_auto_colls', True):
            auto_handler = self.load_auto_colls()
            self.add_route('/_', auto_handler)

        routes = self.load_colls()
        for name, route in iteritems(routes):
            self.add_route('/' + name, route)

        self._add_simple_route('/<coll>-cdx', self.cdx_compat)

        return self

    def _lookup(self, environ, path):
        urls = self.url_map.bind(environ['HTTP_HOST'], path_info=path)

        try:
            endpoint, args = urls.match()
            result = endpoint(environ, **args)
            return result
        except Exception as e:
            print(e)
            return None

    def cdx_compat(self, environ, coll=''):
        """ -cdx server api
        """
        result = self._lookup(environ, '/{0}/index'.format(coll))
        if result:
            return result

        environ['QUERY_STRING'] += '&param.coll=' + coll
        result = self._lookup(environ, '/_/index')
        return result

    def load_auto_colls(self):
        root_dir = self.config.get('collections_root', '')
        if not root_dir:
            print('No Root Dir, Skip Auto Colls!')
            return

        indexes_templ = os.path.join('{coll}', 'indexes') + os.path.sep
        dir_source = CacheDirectoryIndexSource(root_dir, indexes_templ)

        archive_templ = self.config.get('archive_paths')
        if not archive_templ:
            archive_templ = os.path.join('.', root_dir, '{coll}', 'archive') + os.path.sep
        handler = DefaultResourceHandler(dir_source, archive_templ)

        return handler

    def load_colls(self):
        routes = {}

        colls = self.config.get('collections', None)
        if not colls:
            return routes

        for name, coll_config in iteritems(colls):
            handler = self.load_coll(name, coll_config)
            routes[name] = handler

        return routes

    def load_coll(self, name, coll_config):
        if isinstance(coll_config, str):
            index = coll_config
            resource =  None
        elif isinstance(coll_config, dict):
            index = coll_config.get('index')
            resource = coll_config.get('resource')
        else:
            raise Exception('collection config must be string or dict')

        sources = {}
        if index:
            sources[name] = self.load_single_source(index)
            agg = SimpleAggregator(sources)

        else:
            if not isinstance(coll_config, dict):
                raise Exception('collection config missing')

            sequence = coll_config.get('sequence')
            if sequence:
                return self.init_sequence(name, sequence)

            index = coll_config.get('index_group')
            if not index:
                raise Exception('no index, index_group or sequence found')

            for name, value in iteritems(index):
                sources[name] = self.load_single_source(value)

            timeout = int(coll_config.get('timeout', 0))
            agg = GeventTimeoutAggregator(sources, timeout=timeout)

        return DefaultResourceHandler(agg, resource)

    def init_sequence(self, coll_name, seq_config):
        if not isinstance(seq_config, list):
            raise Exception('"sequence" config must be a list')

        handlers = []

        for entry in seq_config:
            if not isinstance(entry, dict):
                raise Exception('"sequence" entry must be a dict')

            name = entry.get('name')
            handler = self.load_coll(name, entry)
            handlers.append(handler)

        return HandlerSeq(handlers)

    def load_single_source(self, value):
        if isinstance(value, str):
            for source_cls in SOURCE_LIST:
                source = source_cls.init_from_string(value)
                if source:
                    return source

        elif isinstance(value, dict):
            for source_cls in SOURCE_LIST:
                source = source_cls.init_from_config(value)
                if source:
                    return source

        else:
            raise Exception('Source config must be string or dict')

        raise Exception('No Index Source Found for: ' + str(value))

