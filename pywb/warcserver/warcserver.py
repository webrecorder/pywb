from pywb.utils.loaders import load_yaml_config, load_overlay_config

from pywb.warcserver.basewarcserver import BaseWarcServer

from pywb.warcserver.http import PywbHttpAdapter, DefaultAdapters
from urllib3.util.retry import Retry

from pywb.warcserver.index.aggregator import CacheDirectoryIndexSource, RedisMultiKeyIndexSource
from pywb.warcserver.index.aggregator import GeventTimeoutAggregator, SimpleAggregator

from pywb.warcserver.handlers import DefaultResourceHandler, HandlerSeq

from pywb.warcserver.index.indexsource import FileIndexSource, RemoteIndexSource
from pywb.warcserver.index.indexsource import MementoIndexSource, RedisIndexSource
from pywb.warcserver.index.indexsource import LiveIndexSource, WBMementoIndexSource
from pywb.warcserver.index.indexsource import XmlQueryIndexSource

from pywb.warcserver.index.zipnum import ZipNumIndexSource

from pywb.warcserver.access_checker import AccessChecker, CacheDirectoryAccessSource

from pywb import DEFAULT_CONFIG

from six import iteritems, iterkeys, itervalues
from six.moves import zip
import os


SOURCE_LIST = [LiveIndexSource,
               XmlQueryIndexSource,
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
    AUTO_COLL_TEMPL = '{coll}'

    DEFAULT_DEDUP_URL = 'redis://localhost:6379/0/pywb:{coll}:cdxj'

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
            if 'proxy' in custom_config and 'proxy' in config:
                custom_config['proxy'].update(config['proxy'])
            if 'recorder' in custom_config and 'recorder' in config:
                if isinstance(custom_config['recorder'], str):
                    custom_config['recorder'] = {'source_coll': custom_config['recorder']}

                if isinstance(config['recorder'], str):
                    config['recorder'] = {'source_coll': config['recorder']}

                config['recorder'].update(custom_config['recorder'])
                custom_config['recorder'] = config['recorder']

            config.update(custom_config)

        super(WarcServer, self).__init__(debug=config.get('debug', False))
        self.config = config

        recorder_config = self.config.get('recorder') or {}
        if isinstance(recorder_config, dict) and recorder_config.get('dedup_policy'):
            self.dedup_index_url = recorder_config.get('dedup_index_url', WarcServer.DEFAULT_DEDUP_URL)
            if self.dedup_index_url and not self.dedup_index_url.startswith('redis://'):
                raise Exception("The dedup_index_url must start with \"redis://\". Only Redis-based dedup index is supported at this time.")
        else:
            self.dedup_index_url = None

        self.root_dir = self.config.get('collections_root', '')
        self.index_paths = self.init_paths('index_paths')
        self.archive_paths = self.init_paths('archive_paths', self.root_dir)
        self.acl_paths = self.init_paths('acl_paths')

        self.default_access = self.config.get('default_access')

        self.rules_file = self.config.get('rules_file', '')

        if 'certificates' in self.config:
            certs_config = self.config['certificates']
            DefaultAdapters.live_adapter = PywbHttpAdapter(max_retries=Retry(3),
                                                           cert_reqs=certs_config.get('cert_reqs', 'CERT_NONE'),
                                                           ca_cert_dir=certs_config.get('ca_cert_dir'))
            DefaultAdapters.remote_adapter = PywbHttpAdapter(max_retries=Retry(3),
                                                             cert_reqs=certs_config.get('cert_reqs', 'CERT_NONE'),
                                                             ca_cert_dir=certs_config.get('ca_cert_dir'))

        self.auto_handler = None

        if self.config.get('enable_auto_colls', True):
            self.auto_handler = self.load_auto_colls()

        self.fixed_routes = self.load_colls()

        for name, route in iteritems(self.fixed_routes):
            if route == self.auto_handler:
                self.add_route('/' + name, route, path_param_name='param.coll', default_value='*')
            else:
                self.add_route('/' + name, route)

        if self.auto_handler:
            self.add_route('/<path_param_value>', self.auto_handler, path_param_name='param.coll')

    def init_paths(self, name, abs_path=None):
        templ = self.config.get(name)

        def get_full_path(path):
            if '://' not in path:
                path = os.path.join(self.AUTO_COLL_TEMPL, path, '')
                if abs_path:
                    path = os.path.join(abs_path, path)
            return path

        if isinstance(templ, str):
            return get_full_path(templ)
        else:
            return [get_full_path(t) for t in templ]

    def load_auto_colls(self):
        if not self.root_dir:
            print('No Root Dir, Skip Auto Colls!')
            return

        dir_source = CacheDirectoryIndexSource(base_prefix=self.root_dir,
                                               base_dir=self.index_paths,
                                               config=self.config)

        access_checker = AccessChecker(CacheDirectoryAccessSource(base_prefix=self.root_dir,
                                                                  base_dir=self.acl_paths,
                                                                  config=self.config),
                                       self.default_access)

        if self.dedup_index_url:
            source = SimpleAggregator({'dedup': RedisMultiKeyIndexSource(self.dedup_index_url),
                                       'dir': dir_source})

        else:
            source = dir_source

        return DefaultResourceHandler(source, self.archive_paths,
                                      rules_file=self.rules_file,
                                      access_checker=access_checker)

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
        if coll_config == '$all' and self.auto_handler:
            return self.auto_handler

        if isinstance(coll_config, str):
            index = coll_config
            archive_paths = None
            acl_paths = None
            default_access = self.default_access
            embargo = None
        elif isinstance(coll_config, dict):
            index = coll_config.get('index')
            if not index:
                index = coll_config.get('index_paths')
            archive_paths = coll_config.get('archive_paths')
            acl_paths = coll_config.get('acl_paths')
            default_access = coll_config.get('default_access', self.default_access)
            embargo = coll_config.get('embargo')

        else:
            raise Exception('collection config must be string or dict')

        # INDEX CONFIG
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

        # ARCHIVE CONFIG
        if not archive_paths:
            archive_paths = self.config.get('archive_paths')
            use_local_file_load = False
        else:
            use_local_file_load = True

        # ACCESS CONFIG
        access_checker = None
        if acl_paths or embargo:
            access_checker = AccessChecker(acl_paths, default_access, embargo)

        return DefaultResourceHandler(agg, archive_paths,
                                      rules_file=self.rules_file,
                                      access_checker=access_checker,
                                      use_local_file_load=use_local_file_load)

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


