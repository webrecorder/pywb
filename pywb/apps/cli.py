from gevent.monkey import patch_all; patch_all()
from argparse import ArgumentParser

import logging


#=============================================================================
def webagg(args=None):
    WarcServerCli(args=args,
              default_port=8070,
              desc='pywb Web Aggregator Server').run()


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

        parser.add_argument('--live', action='store_true', help='Add /live handler')

        self.desc = desc
        self.extra_config = None

        self._extend_parser(parser)

        self.r = parser.parse_args(args)

        logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                            level=logging.DEBUG if self.r.debug else logging.INFO)

        self.application = self.load()

        if self.r.profile:
            from werkzeug.contrib.profiler import ProfilerMiddleware
            self.application = ProfilerMiddleware(self.application)

    def _extend_parser(self, parser):  #pragma: no cover
        pass

    def load(self):
        if self.r.live:
            self.extra_config = {'collections': {'live': '$live'}}

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

        help_dir='Specify root archive dir (default is current working directory)'
        parser.add_argument('-d', '--directory', help=help_dir)


    def load(self):
        super(ReplayCli, self).load()
        import os
        if self.r.directory:  #pragma: no cover
            os.chdir(self.r.directory)

    def run(self):
        if self.r.autoindex:
            from pywb.manager.manager import CollectionsManager
            import os

            m = CollectionsManager('', must_exist=False)
            if not os.path.isdir(m.colls_dir):
                msg = 'No managed directory "{0}" for auto-indexing'
                logging.error(msg.format(m.colls_dir))
                import sys
                sys.exit(2)
            else:
                msg = 'Auto-Indexing Enabled on "{0}", checking every {1} secs'
                logging.info(msg.format(m.colls_dir, self.r.auto_interval))
                m.autoindex(interval=self.r.auto_interval, do_loop=False)

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
