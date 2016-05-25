from gevent.monkey import patch_all; patch_all()

from webagg.test.testutils import LiveServerTests
from webagg.handlers import DefaultResourceHandler
from webagg.app import ResAggApp
from webagg.indexsource import LiveIndexSource, RedisIndexSource
from webagg.aggregator import SimpleAggregator, CacheDirectoryIndexSource

def simpleapp():
    app = ResAggApp(debug=True)
    app.add_route('/live',
        DefaultResourceHandler(SimpleAggregator(
                               {'live': LiveIndexSource()})
        )
    )

    app.add_route('/replay',
        DefaultResourceHandler(SimpleAggregator(
                               {'replay': RedisIndexSource('redis://localhost/2/rec:cdxj')}),
                                'redis://localhost/2/rec:warc'
        )
    )

    app.add_route('/replay-testdata',
        DefaultResourceHandler(SimpleAggregator(
                               {'test': CacheDirectoryIndexSource('./testdata/')}),
                                './testdata/'
        )
    )
    return app



application = simpleapp()


if __name__ == "__main__":
#    from bottle import run
#    run(application, server='gevent', port=8080, fast=True)

    from gevent.wsgi import WSGIServer
    server = WSGIServer(('', 8080), application)
    server.serve_forever()

