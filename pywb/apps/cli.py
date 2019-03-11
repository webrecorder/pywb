from gevent.monkey import patch_all; patch_all()
from argparse import ArgumentParser

import logging


#=============================================================================
def warcserver(args=None):
    """Utility function for starting pywb's WarcServer"""
    return WarcServerCli(args=args,
                         default_port=8070,
                         desc='pywb WarcServer').run()


#=============================================================================
def wayback(args=None):
    """Utility function for starting pywb's Wayback Machine implementation"""
    return WaybackCli(args=args,
                      default_port=8080,
                      desc='pywb Wayback Machine Server').run()


#=============================================================================
def live_rewrite_server(args=None):
    """Utility function for starting pywb's Wayback Machine implementation in live mode"""
    return LiveCli(args=args,
                   default_port=8090,
                   desc='pywb Live Rewrite Proxy Server').run()


#=============================================================================
class BaseCli(object):
    """Base CLI class that provides the initial arg parser setup,
    calls load to receive the application to be started and starts the application."""

    def __init__(self, args=None, default_port=8080, desc=''):
        """
        :param args: CLI arguments
        :param int default_port: The default port that the application will use
        :param str desc: The description for the application to be started
        """
        parser = ArgumentParser(description=desc)
        parser.add_argument('-p', '--port', type=int, default=default_port,
                            help='Port to listen on (default %s)' % default_port)
        parser.add_argument('-b', '--bind', default='0.0.0.0',
                            help='Address to listen on (default 0.0.0.0)')
        parser.add_argument('-t', '--threads', type=int, default=4,
                            help='Number of threads to use (default 4)')
        parser.add_argument('--debug', action='store_true',
                            help='Enable debug mode')
        parser.add_argument('--profile', action='store_true',
                            help='Enable profile mode')
        parser.add_argument('--live', action='store_true',
                            help='Add live-web handler at /live')
        parser.add_argument('--record', action='store_true',
                            help='Enable recording from the live web')
        parser.add_argument('--proxy',
                            help='Enable HTTP/S proxy on specified collection')
        parser.add_argument('-pt', '--proxy-default-timestamp',
                            help='Default timestamp / ISO date to use for proxy requests')
        parser.add_argument('--proxy-record', action='store_true',
                            help='Enable proxy recording into specified collection')
        parser.add_argument('--proxy-enable-wombat', action='store_true',
                            help='Enable partial wombat JS overrides support in proxy mode')
        parser.add_argument('--enable-auto-fetch', action='store_true',
                            help='Enable auto-fetch worker to capture resources from stylesheets, <img srcset> when running in live/recording mode')

        self.desc = desc
        self.extra_config = {}

        self._extend_parser(parser)

        self.r = parser.parse_args(args)

        logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                            level=logging.DEBUG if self.r.debug else logging.INFO)
        if self.r.proxy:
            self.extra_config['proxy'] = {
                'coll': self.r.proxy,
                'recording': self.r.proxy_record,
                'enable_wombat': self.r.proxy_enable_wombat,
                'default_timestamp': self.r.proxy_default_timestamp,
            }

            self.r.live = True

        self.extra_config['enable_auto_fetch'] = self.r.enable_auto_fetch

        self.application = self.load()

        if self.r.profile:
            from werkzeug.contrib.profiler import ProfilerMiddleware
            self.application = ProfilerMiddleware(self.application)

    def _extend_parser(self, parser):  #pragma: no cover
        """Method provided for subclasses to add their cli argument on top of the default cli arguments.

        :param ArgumentParser parser: The argument parser instance passed by BaseCli
        """
        pass

    def load(self):
        """This method is called to load the application. Subclasses must return a application
        that can be used by used by pywb.utils.geventserver.GeventServer."""
        if self.r.live:
            self.extra_config['collections'] = {'live':
                    {'index': '$live'}}

        if self.r.debug:
            self.extra_config['debug'] = True

        if self.r.record:
            self.extra_config['recorder'] = 'live'

    def run(self):
        """Start the application"""
        self.run_gevent()
        return self

    def run_gevent(self):
        """Created the server that runs the application supplied a subclass"""
        from pywb.utils.geventserver import GeventServer, RequestURIWSGIHandler
        logging.info('Starting Gevent Server on ' + str(self.r.port))
        ge = GeventServer(self.application,
                          port=self.r.port,
                          hostname=self.r.bind,
                          handler_class=RequestURIWSGIHandler,
                          direct=True)


#=============================================================================
class ReplayCli(BaseCli):
    """CLI class that adds the cli functionality specific to starting pywb's Wayback Machine implementation"""

    def _extend_parser(self, parser):
        parser.add_argument('-a', '--autoindex', action='store_true',
                            help='Enable auto-indexing')
        parser.add_argument('--auto-interval', type=int, default=30,
                            help='Auto-indexing interval (default 30 seconds)')

        parser.add_argument('--all-coll', help='Set "all" collection')

        help_dir='Specify root archive dir (default is current working directory)'
        parser.add_argument('-d', '--directory', help=help_dir)

    def load(self):
        super(ReplayCli, self).load()

        if self.r.all_coll:
            if 'collections' not in self.extra_config:
                self.extra_config['collections'] = {}
            self.extra_config['collections'][self.r.all_coll] = '$all'

        if self.r.autoindex:
            self.extra_config['autoindex'] = self.r.auto_interval

        import os
        if self.r.directory:  #pragma: no cover
            os.chdir(self.r.directory)


#=============================================================================
class WarcServerCli(BaseCli):
    """CLI class for starting a WarcServer"""

    def load(self):
        from pywb.warcserver.warcserver import WarcServer

        super(WarcServerCli, self).load()
        return WarcServer(custom_config=self.extra_config)


#=============================================================================
class WaybackCli(ReplayCli):
    """CLI class for starting the pywb's implementation of the Wayback Machine"""

    def load(self):
        from pywb.apps.frontendapp import FrontEndApp

        super(WaybackCli, self).load()
        return FrontEndApp(custom_config=self.extra_config)


#=============================================================================
class LiveCli(BaseCli):
    """CLI class for starting pywb in replay server in live mode"""

    def load(self):
        from pywb.apps.frontendapp import FrontEndApp

        self.r.live = True

        super(LiveCli, self).load()
        return FrontEndApp(config_file=None, custom_config=self.extra_config)


#=============================================================================
if __name__ == "__main__":
    wayback()
