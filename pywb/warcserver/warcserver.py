from pywb.utils.loaders import load_yaml_config, load_overlay_config

from pywb.warcserver.basewarcserver import BaseWarcServer

from pywb.warcserver.index.aggregator import CacheDirectoryIndexSource, RedisMultiKeyIndexSource
from pywb.warcserver.index.aggregator import GeventTimeoutAggregator, SimpleAggregator

from pywb.warcserver.handlers import DefaultResourceHandler, HandlerSeq

from pywb.warcserver.index.indexsource import FileIndexSource, RemoteIndexSource
from pywb.warcserver.index.indexsource import MementoIndexSource, RedisIndexSource
from pywb.warcserver.index.indexsource import LiveIndexSource, WBMementoIndexSource
from pywb.warcserver.index.zipnum import ZipNumIndexSource

from pywb import DEFAULT_CONFIG

from six import iteritems, iterkeys, itervalues
from six.moves import zip
import os


SOURCE_LIST = [LiveIndexSource,
               WBMementoIndexSource,
               RedisMultiKeyIndexSource,
               MementoIndexSource,
               CacheDirectoryIndexSource,
               FileIndexSource,
               RemoteIndexSource,
               ZipNumIndexSource,
              ]


# ============================================================================
class WarcServer(BaseWarcServer):
    AUTO_DIR_INDEX_PATH = '{coll}/indexes/'
    AUTO_DIR_ARCHIVE_PATH = '{coll}/archive/'

    def __init__(self, config_file='./config.yaml', custom_config=None):
        config = load_yaml_config(DEFAULT_CONFIG)

        if config_file:
            try:
                file_config = load_overlay_config('PYWB_CONFIG_FILE', config_file)
                config.update(file_config)
            except Exception as e:
                if not custom_config:
                    custom_config = {'debug': True}
                print(e)

        if custom_config:
            if 'collections' in custom_config and 'collections' in config:
                custom_config['collections'].update(config['collections'])
            config.update(custom_config)

        super(WarcServer, self).__init__(debug=config.get('debug', False))
        self.config = config

        self.fixed_routes = self.load_colls()

        self.archive_templ = None
        self.indexes_templ = None

        for name, route in iteritems(self.fixed_routes):
            self.add_route('/' + name, route)

        if self.config.get('enable_auto_colls', True):
            auto_handler = self.load_auto_colls()
            self.add_route('/<path:path_param_value>', auto_handler, path_param_name='param.coll')

    def _lookup(self, environ, path):
        urls = self.url_map.bind(environ['HTTP_HOST'], path_info=path)

        try:
            endpoint, args = urls.match()
            result = endpoint(environ, **args)
            return result
        except Exception as e:
            print(e)
            return None

    def load_auto_colls(self):
        self.root_dir = self.config.get('collections_root', '')
        if not self.root_dir:
            print('No Root Dir, Skip Auto Colls!')
            return

        self.indexes_templ = self.config.get('dyn_index_path', self.AUTO_DIR_INDEX_PATH).replace('/', os.path.sep)

        dir_source = CacheDirectoryIndexSource(base_prefix=self.root_dir,
                                               base_dir=self.indexes_templ)

        self.archive_templ = self.config.get('dyn_archive_path', self.AUTO_DIR_ARCHIVE_PATH).replace('/', os.path.sep)
        if '://' not in self.archive_templ:
            self.archive_templ = os.path.join(self.root_dir, self.archive_templ)

        handler = DefaultResourceHandler(dir_source, self.archive_templ)

        return handler

    def list_fixed_routes(self):
        return list(self.fixed_routes.keys())

    def get_coll_config(self, name):
        colls = self.config.get('collections', None)
        if not colls:
            return {}

        res = colls.get(name, {})
        if not isinstance(res, dict):
            res = {'index': res}
        return res

    def list_dynamic_routes(self):
        if not self.root_dir:
            return []

        try:
            return os.listdir(self.root_dir)
        except (IOError, OSError):
            return []

    def load_colls(self):
        routes = {}

        colls = self.config.get('collections', None)
        if not colls:
            return routes

        self.default_archive_paths = self.config.get('archive_paths')

        for name, coll_config in iteritems(colls):
            try:
                handler = self.load_coll(name, coll_config)
            except:
                print('Invalid Collection: ' + name)
                if self.debug:
                    import traceback
                    traceback.print_exc()
                continue

            routes[name] = handler

        return routes

    def load_coll(self, name, coll_config):
        if isinstance(coll_config, str):
            index = coll_config
            resource = None
        elif isinstance(coll_config, dict):
            index = coll_config.get('index')
            if not index:
                index = coll_config.get('index_paths')
            resource = coll_config.get('resource')
            if not resource:
                resource = coll_config.get('archive_paths')

        else:
            raise Exception('collection config must be string or dict')

        if index:
            agg = init_index_agg({name: index})

        else:
            if not isinstance(coll_config, dict):
                raise Exception('collection config missing')

            sequence = coll_config.get('sequence')
            if sequence:
                return self.init_sequence(name, sequence)

            index_group = coll_config.get('index_group')
            if not index_group:
                raise Exception('no index, index_group or sequence found')

            timeout = int(coll_config.get('timeout', 0))
            agg = init_index_agg(index_group, True, timeout)

        if not resource:
            resource = self.default_archive_paths

        return DefaultResourceHandler(agg, resource)

    def init_sequence(self, coll_name, seq_config):
        if not isinstance(seq_config, list):
            raise Exception('"sequence" config must be a list')

        handlers = []

        for entry in seq_config:
            if not isinstance(entry, dict):
                raise Exception('"sequence" entry must be a dict')

            name = entry.get('name', '')
            handler = self.load_coll(name, entry)
            handlers.append(handler)

        return HandlerSeq(handlers)

# ============================================================================
def init_index_source(value, source_list=None):
    source_list = source_list or SOURCE_LIST
    if isinstance(value, str):
        for source_cls in source_list:
            source = source_cls.init_from_string(value)
            if source:
                return source

    elif isinstance(value, dict):
        for source_cls in source_list:
            source = source_cls.init_from_config(value)
            if source:
                return source

    else:
        raise Exception('Source config must be string or dict')

    raise Exception('No Index Source Found for: ' + str(value))


# ============================================================================
def register_source(source_cls, end=False):
    if not end:
        SOURCE_LIST.insert(0, source_cls)
    else:
        SOURCE_LIST.append(source_cls)


# ============================================================================
def init_index_agg(source_configs, use_gevent=False, timeout=0, source_list=None):
    sources = {}
    for n, v in iteritems(source_configs):
        sources[n] = init_index_source(v, source_list=source_list)

    if use_gevent:
        return GeventTimeoutAggregator(sources, timeout=timeout)
    else:
        return SimpleAggregator(sources)


