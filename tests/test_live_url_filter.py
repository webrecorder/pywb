from gevent import monkey; monkey.patch_all(thread=False)

import glob
import gzip
import os
import time

import pytest
import webtest
from mock import patch

from pywb.apps.frontendapp import FrontEndApp
from pywb.warcserver import liveconnectguard
from pywb.warcserver.liveurlfilter import LiveUrlFilter
from pywb.warcserver.test.liveguardutils import FakeDNS, LocalServer, PUBLIC_IP, RedirectConnections


# ============================================================================
class RebindingDNS(FakeDNS):
    """rebinding domain answering the public address to the filter lookups
    (no port) and the loopback address to every lookup when connecting"""
    def __call__(self, host, port, family=0, type=0, proto=0, flags=0):
        if host == 'rebind.example.com':
            self.hosts[host] = [PUBLIC_IP] if port is None else ['127.0.0.1']
        return super(RebindingDNS, self).__call__(host, port, family, type, proto, flags)


def read_warcs(collections_root):
    data = b''
    for name in glob.glob(os.path.join(collections_root, '*', 'archive', '*.warc.gz')):
        with gzip.open(name) as fh:
            data += fh.read()
    return data


def wait_for_warcs(collections_root, *contents):
    # wait for the recorder to write and close the WARC
    for _ in range(50):
        warcs = read_warcs(collections_root)
        if any(content in warcs for content in contents):
            return warcs
        time.sleep(0.1)

    return read_warcs(collections_root)


@pytest.fixture
def record_app(tmp_path, monkeypatch):
    for name in ('PYWB_LIVE_BLOCKED_DOMAINS', 'PYWB_LIVE_BLOCKED_NETWORKS', 'PYWB_LIVE_CONNECT_GUARD'):
        monkeypatch.delenv(name, raising=False)

    collections_root = str(tmp_path / 'collections')
    for name in ('archive', 'indexes'):
        os.makedirs(os.path.join(collections_root, 'test', name))

    dns = RebindingDNS({'public.example.com': [PUBLIC_IP]})

    with LocalServer(files={'/page': b'PUBLIC PAGE'}) as server, patch('socket.getaddrinfo', dns):
        redirect = RedirectConnections(server.port, liveconnectguard.create_connection)

        def make_app(live_url_filter):
            app = FrontEndApp(custom_config={
                'collections_root': collections_root,
                'collections': {'live': '$live'},
                'recorder': {
                    'source_coll': 'live',
                    'rollover_idle_secs': 1,
                    'filename_template': 'live-{timestamp}-{random}.warc.gz',
                },
                'live_url_filter': live_url_filter,
            })
            return app, webtest.TestApp(app)

        with patch('pywb.warcserver.liveconnectguard.create_connection', redirect):
            yield make_app, collections_root, server, redirect, dns

    LiveUrlFilter.init(None)


# ============================================================================
def test_record_public_page(record_app):
    make_app, collections_root, server, redirect, dns = record_app
    app, testapp = make_app(True)

    # recorded through the recorder calls to the internal warcserver on localhost
    resp = testapp.get('/test/record/id_/http://public.example.com:%d/page' % server.port)
    assert resp.text == 'PUBLIC PAGE'

    assert b'PUBLIC PAGE' in wait_for_warcs(collections_root, b'PUBLIC PAGE')
    assert redirect.addresses == [PUBLIC_IP]
    app.recorder.writer.close()


@pytest.mark.parametrize('url', ['http://127.0.0.1:{port}/secret', 'http://localhost:{port}/secret',
                                 'http://[::1]:{port}/secret', 'http://0x7f.1:{port}/secret'])
def test_record_internal_blocked(record_app, url):
    make_app, collections_root, server, redirect, dns = record_app
    app, testapp = make_app(True)

    resp = testapp.get('/test/record/id_/' + url.format(port=server.port), status='*')
    assert resp.status_int >= 400
    assert b'INTERNAL SECRET' not in resp.body

    assert server.requests == []
    assert b'INTERNAL SECRET' not in read_warcs(collections_root)
    app.recorder.writer.close()


def test_record_rebinding_without_guard(record_app):
    # the rebinding domain is allowed by the filter, and recorded from loopback
    make_app, collections_root, server, redirect, dns = record_app
    app, testapp = make_app({'connect_guard': False})

    resp = testapp.get('/test/record/id_/http://rebind.example.com:%d/secret' % server.port)
    assert resp.text == 'INTERNAL SECRET'

    assert b'INTERNAL SECRET' in wait_for_warcs(collections_root, b'INTERNAL SECRET')
    app.recorder.writer.close()


def test_record_rebinding_blocked(record_app, caplog):
    make_app, collections_root, server, redirect, dns = record_app
    app, testapp = make_app(True)

    resp = testapp.get('/test/record/id_/http://rebind.example.com:%d/secret' % server.port, status='*')
    assert resp.status_int >= 400
    assert b'INTERNAL SECRET' not in resp.body

    # allowed by the filter, but the connection is blocked
    assert [PUBLIC_IP] in dns.lookups_for('rebind.example.com')
    assert ['127.0.0.1'] in dns.lookups_for('rebind.example.com')
    assert server.requests == []
    assert redirect.addresses == []
    assert b'INTERNAL SECRET' not in read_warcs(collections_root)
    assert 'live_url_filter blocked: connection to rebind.example.com' in caplog.text
    app.recorder.writer.close()
