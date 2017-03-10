from argparse import ArgumentParser
import logging


#=================================================================
def cdx_server(args=None):  #pragma: no cover
    CdxCli(args=args,
           default_port=8080,
           desc='pywb CDX Index Server').run()


#=================================================================
def live_rewrite_server(args=None):  #pragma: no cover
    NewLiveCli(args=args,
            default_port=8090,
            desc='pywb Live Rewrite Proxy Server').run()


#=================================================================
def wayback(args=None):
    WaybackCli(args=args,
               default_port=8080,
               desc='pywb Wayback Web Archive Replay').run()


#=============================================================================
def webagg():
    WebaggCli().run()


#=============================================================================
def new_wayback():
    NewWaybackCli().run()


#=============================================================================
class BaseCli(object):
    def __init__(self, args=None, default_port=8080, desc=''):
        parser = ArgumentParser(description=desc)
        parser.add_argument('-p', '--port', type=int, default=default_port)
        parser.add_argument('-t', '--threads', type=int, default=4)
        parser.add_argument('-s', '--server', default='gevent')
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--profile', action='store_true')

        self.desc = desc

        self._extend_parser(parser)

        self.r = parser.parse_args(args)

        logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                            level=logging.DEBUG if self.r.debug else logging.INFO)

        if self.r.server == 'gevent':
            try:
                from gevent.monkey import patch_all; patch_all()
                logging.debug('Using Gevent')
            except:
                logging.debug('No Gevent')
                self.r.server = 'wsgiref'

        self.application = self.load()

        if self.r.profile:
            from werkzeug.contrib.profiler import ProfilerMiddleware
            self.application = ProfilerMiddleware(self.application)

    def _extend_parser(self, parser):  #pragma: no cover
        pass

    def load(self):  #pragma: no cover
        pass

    def run(self):
        if self.r.server == 'gevent':  #pragma: no cover
            self.run_gevent()
        elif self.r.server == 'waitress':  #pragma: no cover
            self.run_waitress()
        else:
            self.run_wsgiref()

    def run_waitress(self):  #pragma: no cover
        from waitress import serve
        logging.debug(str(self.desc))
        serve(self.application, port=self.r.port, threads=self.r.threads)

    def run_wsgiref(self):  #pragma: no cover
        from pywb.framework.wsgi_wrappers import start_wsgi_ref_server
        start_wsgi_ref_server(self.application, self.desc, port=self.r.port)

    def run_gevent(self):
        from gevent.pywsgi import WSGIServer
        logging.info('Starting Gevent Server on ' + str(self.r.port))
        WSGIServer(('', self.r.port), self.application).serve_forever()


#=============================================================================
class LiveCli(BaseCli):
    def _extend_parser(self, parser):
        parser.add_argument('-x', '--proxy',
                            help='Specify host:port to use as HTTP/S proxy')

        parser.add_argument('-f', '--framed', action='store_true',
                            help='Replay using framed wrapping mode')

    def load(self):
        config = dict(proxyhostport=self.r.proxy,
                      framed_replay='inverse' if self.r.framed else False,
                      enable_auto_colls=False,
                      collections={'live': '$liveweb'})

        from pywb.webapp.pywb_init import create_wb_router
        from pywb.framework.wsgi_wrappers import init_app

        return init_app(create_wb_router, load_yaml=False, config=config)


#=============================================================================
class ReplayCli(BaseCli):
    def _extend_parser(self, parser):
        parser.add_argument('-a', '--autoindex', action='store_true')
        parser.add_argument('--auto-interval', type=int, default=30)

        help_dir='Specify root archive dir (default is current working directory)'
        parser.add_argument('-d', '--directory', help=help_dir)


    def load(self):
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
class CdxCli(ReplayCli):  #pragma: no cover
    def load(self):
        from pywb.webapp.pywb_init import create_cdx_server_app
        from pywb.framework.wsgi_wrappers import init_app
        super(CdxCli, self).load()
        return init_app(create_cdx_server_app,
                        load_yaml=True)


#=============================================================================
class WaybackCli(ReplayCli):
    def load(self):
        from pywb.webapp.pywb_init import create_wb_router
        from pywb.framework.wsgi_wrappers import init_app
        super(WaybackCli, self).load()
        return init_app(create_wb_router,
                        load_yaml=True)


#=============================================================================
class WebaggCli(BaseCli):
    def load(self):
        from pywb.apps.webagg import application
        return application

    def run(self):
        self.run_gevent()


#=============================================================================
class NewWaybackCli(ReplayCli):
    def load(self):
        from pywb.apps.newwayback import application
        return application

    def run(self):
        self.r.server = 'gevent'
        super(NewWaybackCli, self).run()
        #self.run_gevent()

#=============================================================================
class NewLiveCli(BaseCli):
    def load(self):
        from pywb.apps.live import application
        return application

    def run(self):
        self.r.server = 'gevent'
        super(NewLiveCli, self).run()
        #self.run_gevent()




#=============================================================================
if __name__ == "__main__":
    wayback()
