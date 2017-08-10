from gevent.monkey import patch_all; patch_all()
from argparse import ArgumentParser

import logging


#=============================================================================
def warcserver(args=None):
    WarcServerCli(args=args,
              default_port=8070,
              desc='pywb WarcServer').run()


#=============================================================================
def wayback(args=None):
    WaybackCli(args=args,
               default_port=8080,
               desc='pywb Wayback Machine Server').run()


#=============================================================================
def live_rewrite_server(args=None):
    LiveCli(args=args,
            default_port=8090,
            desc='pywb Live Rewrite Proxy Server').run()


#=============================================================================
class BaseCli(object):
    def __init__(self, args=None, default_port=8080, desc=''):
        parser = ArgumentParser(description=desc)
        parser.add_argument('-p', '--port', type=int, default=default_port)
        parser.add_argument('-t', '--threads', type=int, default=4)
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--profile', action='store_true')

        parser.add_argument('--live', action='store_true', help='Add live-web handler at /live')

        parser.add_argument('--proxy', help='Enable HTTP/S Proxy on specified collection')

        self.desc = desc
        self.extra_config = {}

        self._extend_parser(parser)

        self.r = parser.parse_args(args)

        logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                            level=logging.DEBUG if self.r.debug else logging.INFO)

        self.application = self.load()

        if self.r.proxy:
            self.application = self.application.init_proxy(self.r.proxy)

        if self.r.profile:
            from werkzeug.contrib.profiler import ProfilerMiddleware
            self.application = ProfilerMiddleware(self.application)

    def _extend_parser(self, parser):  #pragma: no cover
        pass

    def load(self):
        if self.r.live:
            self.extra_config['collections'] = {'live':
                    {'index': '$live',
                     'use_js_obj_proxy': True}}

        if self.r.debug:
            self.extra_config['debug'] = True

    def run(self):
        self.run_gevent()

    def run_gevent(self):
        from gevent.pywsgi import WSGIServer
        logging.info('Starting Gevent Server on ' + str(self.r.port))
        WSGIServer(('', self.r.port), self.application).serve_forever()


#=============================================================================
class ReplayCli(BaseCli):
    def _extend_parser(self, parser):
        parser.add_argument('-a', '--autoindex', action='store_true')
        parser.add_argument('--auto-interval', type=int, default=30)

        parser.add_argument('--all-coll', help='Set "all" collection')

        help_dir='Specify root archive dir (default is current working directory)'
        parser.add_argument('-d', '--directory', help=help_dir)


    def load(self):
        super(ReplayCli, self).load()

        if self.r.all_coll:
            self.extra_config['all_coll'] = self.r.all_coll

        import os
        if self.r.directory:  #pragma: no cover
            os.chdir(self.r.directory)

    def run(self):
        if self.r.autoindex:
            from pywb.manager.autoindex import AutoIndexer
            import os

            indexer = AutoIndexer(interval=self.r.auto_interval)
            if not os.path.isdir(indexer.root_path):
                msg = 'No managed directory "{0}" for auto-indexing'
                logging.error(msg.format(indexer.root_path))
                import sys
                sys.exit(2)

            msg = 'Auto-Indexing Enabled on "{0}", checking every {1} secs'
            logging.info(msg.format(indexer.root_path, self.r.auto_interval))
            indexer.start()

        super(ReplayCli, self).run()


#=============================================================================
class WarcServerCli(BaseCli):
    def load(self):
        from pywb.warcserver.warcserver import WarcServer

        super(WarcServerCli, self).load()
        return WarcServer(custom_config=self.extra_config)


#=============================================================================
class WaybackCli(ReplayCli):
    def load(self):
        from pywb.apps.frontendapp import FrontEndApp

        super(WaybackCli, self).load()
        return FrontEndApp(custom_config=self.extra_config)


#=============================================================================
class LiveCli(BaseCli):
    def load(self):
        from pywb.apps.frontendapp import FrontEndApp

        self.r.live = True

        super(LiveCli, self).load()
        return FrontEndApp(config_file=None, custom_config=self.extra_config)


#=============================================================================
if __name__ == "__main__":
    wayback()
