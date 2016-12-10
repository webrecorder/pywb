from argparse import ArgumentParser

#=================================================================
def cdx_server(args=None):  #pragma: no cover
    CdxCli(args=args,
           default_port=8080,
           desc='pywb CDX Index Server').run()


#=================================================================
def live_rewrite_server(args=None):  #pragma: no cover
    LiveCli(args=args,
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
class BaseCli(object):
    def __init__(self, args=None, default_port=8080, desc=''):
        parser = ArgumentParser(description=desc)
        parser.add_argument('-p', '--port', type=int, default=default_port)
        parser.add_argument('-t', '--threads', type=int, default=4)
        parser.add_argument('-s', '--server', default='gevent')

        self.desc = desc

        self._extend_parser(parser)

        self.r = parser.parse_args(args)

        if self.r.server == 'gevent':
            try:
                from gevent.monkey import patch_all; patch_all()
                print('Using Gevent')
            except:
                print('No Gevent')
                self.r.server = 'wsgiref'

        from pywb.framework.wsgi_wrappers import init_app
        self.init_app = init_app

        self.application = self.load()

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
        print(self.desc)
        serve(self.application, port=self.r.port, threads=self.r.threads)

    def run_wsgiref(self):  #pragma: no cover
        from pywb.framework.wsgi_wrappers import start_wsgi_ref_server
        start_wsgi_ref_server(self.application, self.desc, port=self.r.port)

    def run_gevent(self):
        from gevent.pywsgi import WSGIServer
        print('Starting Gevent Server on ' + str(self.r.port))
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
        return self.init_app(create_wb_router, load_yaml=False, config=config)


#=============================================================================
class ReplayCli(BaseCli):
    def _extend_parser(self, parser):
        parser.add_argument('-a', '--autoindex', action='store_true')

        help_dir='Specify root archive dir (default is current working directory)'
        parser.add_argument('-d', '--directory', help=help_dir)


    def load(self):
        if self.r.directory:  #pragma: no cover
            os.chdir(self.r.directory)

    def run(self):
        if self.r.autoindex:
            from pywb.manager.manager import CollectionsManager
            import os
            import logging

            m = CollectionsManager('', must_exist=False)
            if not os.path.isdir(m.colls_dir):
                msg = 'No managed directory "{0}" for auto-indexing'
                logging.error(msg.format(m.colls_dir))
                import sys
                sys.exit(2)
            else:
                msg = 'Auto-Indexing Enabled on "{0}"'
                logging.info(msg.format(m.colls_dir))
                m.autoindex(do_loop=False)

        super(ReplayCli, self).run()

#=============================================================================
class CdxCli(ReplayCli):  #pragma: no cover
    def load(self):
        from pywb.webapp.pywb_init import create_cdx_server_app
        super(CdxCli, self).load()
        return self.init_app(create_cdx_server_app,
                             load_yaml=True)


#=============================================================================
class WaybackCli(ReplayCli):
    def load(self):
        from pywb.webapp.pywb_init import create_wb_router
        super(WaybackCli, self).load()
        return self.init_app(create_wb_router,
                             load_yaml=True)


#=============================================================================
class WebaggCli(BaseCli):
    def load(self):
        from pywb.apps.webagg import application
        return application

    def run(self):
        self.run_gevent()


#=============================================================================
if __name__ == "__main__":
    wayback()
