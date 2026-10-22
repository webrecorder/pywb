from gevent import monkey; monkey.patch_all()

import logging
import socket
from io import BytesIO

import pytest
import requests
from mock import patch
from urllib3 import PoolManager
from urllib3.exceptions import ConnectTimeoutError, NewConnectionError
from urllib3.poolmanager import pool_classes_by_scheme
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter
from werkzeug.test import Client
from werkzeug.wrappers import Response

from pywb.indexer.cdxindexer import write_cdx_index
from pywb.utils.loaders import BlockLoader
from pywb.utils.wbexception import LiveResourceException
from pywb.warcserver.http import DefaultAdapters, PywbHttpAdapter
from pywb.warcserver.index.indexsource import RemoteIndexSource
from pywb.warcserver import liveconnectguard
from pywb.warcserver.liveconnectguard import (GuardedHTTPConnection, GuardedHTTPConnectionPool,
                                              GuardedHTTPSConnectionPool, LiveConnectGuard)
from pywb.warcserver.liveurlfilter import LiveUrlFilter
from pywb.warcserver.resource.responseloader import LiveWebLoader
from pywb.warcserver.warcserver import WarcServer

from .liveguardutils import FakeDNS, LocalServer, PUBLIC_IP, PUBLIC_IP_2, PUBLIC_IPV6, RedirectConnections


GUARDED_POOL_CLASSES = {'http': GuardedHTTPConnectionPool, 'https': GuardedHTTPSConnectionPool}


@pytest.fixture(autouse=True)
def builtin_filter(monkeypatch):
    for name in ('PYWB_LIVE_BLOCKED_DOMAINS', 'PYWB_LIVE_BLOCKED_NETWORKS', 'PYWB_LIVE_CONNECT_GUARD',
                 'SOCKS_HOST'):
        monkeypatch.delenv(name, raising=False)

    adapters = (DefaultAdapters.live_adapter, DefaultAdapters.remote_load_adapter, DefaultAdapters.remote_adapter)
    LiveUrlFilter.init({'blocked_domains': ['internal.example.org']})
    yield
    LiveUrlFilter.init(None)
    (DefaultAdapters.live_adapter, DefaultAdapters.remote_load_adapter,
     DefaultAdapters.remote_adapter) = adapters


@pytest.fixture
def server():
    with LocalServer() as server:
        yield server


@pytest.fixture
def dns():
    dns = FakeDNS({
        'public.example.com': [PUBLIC_IP],
        'mixed.example.com': ['127.0.0.1', '10.1.2.3', PUBLIC_IP, '192.168.0.1', PUBLIC_IP_2, PUBLIC_IPV6],
        # rebinding domain: public address on the first lookup, loopback next
        'rebind.example.com': [[PUBLIC_IP], ['127.0.0.1']],
        'internal.example.com': ['127.0.0.1'],
        'warcs.internal.example.org': ['127.0.0.1'],
    })
    with patch('socket.getaddrinfo', dns):
        yield dns


@pytest.fixture
def redirect(server):
    redirect = RedirectConnections(server.port, liveconnectguard.create_connection)
    with patch('pywb.warcserver.liveconnectguard.create_connection', redirect):
        yield redirect


def live_get(url, is_live=True):
    """request ``url`` as pywb does for a live (or remote archive) load"""
    return LiveWebLoader()._do_request('GET', url, None, {}, {}, is_live)


def assert_blocked_logged(caplog, host):
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(m.startswith('live_url_filter blocked: connection to ' + host) for m in messages), messages


# Adapters
def test_default_adapters():
    assert DefaultAdapters.live_adapter.poolmanager.pool_classes_by_scheme == GUARDED_POOL_CLASSES
    assert DefaultAdapters.remote_load_adapter.poolmanager.pool_classes_by_scheme == GUARDED_POOL_CLASSES
    # remote indexes are set on the config, not checked
    assert DefaultAdapters.remote_adapter.poolmanager.pool_classes_by_scheme is pool_classes_by_scheme


def test_urllib3_default_pool_classes_not_changed():
    assert pool_classes_by_scheme['http'].__name__ == 'HTTPConnectionPool'
    assert pool_classes_by_scheme['https'].__name__ == 'HTTPSConnectionPool'
    assert PoolManager().pool_classes_by_scheme is pool_classes_by_scheme
    assert PywbHttpAdapter().poolmanager.pool_classes_by_scheme is pool_classes_by_scheme


def test_certificates_config_adapters():
    WarcServer(config_file=None, custom_config={
        'certificates': {'cert_reqs': 'CERT_REQUIRED'},
        'live_url_filter': True,
        'enable_auto_colls': False,
    })

    for adapter in (DefaultAdapters.live_adapter, DefaultAdapters.remote_load_adapter, DefaultAdapters.remote_adapter):
        assert adapter.cert_reqs == 'CERT_REQUIRED'

    assert DefaultAdapters.live_adapter.poolmanager.pool_classes_by_scheme == GUARDED_POOL_CLASSES
    assert DefaultAdapters.remote_load_adapter.poolmanager.pool_classes_by_scheme == GUARDED_POOL_CLASSES
    assert DefaultAdapters.remote_adapter.poolmanager.pool_classes_by_scheme is pool_classes_by_scheme
    assert LiveConnectGuard.is_ip_blocked == LiveUrlFilter.func.is_ip_blocked


def test_not_installed_connects_to_any_address(dns, server):
    LiveUrlFilter.init(None)

    res = live_get('http://internal.example.com:%d/' % server.port)
    assert res.status == 200
    assert res.read() == b'INTERNAL SECRET'


# DNS rebinding
def test_rebinding_reproduction_without_guard(dns, server):
    # the filter sees the public address, urllib3 connects to loopback
    url = 'http://rebind.example.com:%d/' % server.port
    assert LiveUrlFilter.is_allowed(url) is True
    res = PoolManager().request('GET', url, retries=False)
    assert res.status == 200
    assert res.data == b'INTERNAL SECRET'


@pytest.mark.parametrize('is_live', [True, False])
def test_rebinding_blocked(dns, server, caplog, is_live):
    url = 'http://rebind.example.com:%d/' % server.port
    assert LiveUrlFilter.is_allowed(url) is True

    with pytest.raises(LiveResourceException):
        live_get(url, is_live)

    assert server.requests == []
    # one lookup by the filter, then one per connection attempt (Retry(3))
    assert dns.lookups_for('rebind.example.com') == [[PUBLIC_IP]] + [['127.0.0.1']] * 4
    assert_blocked_logged(caplog, 'rebind.example.com:%d' % server.port)


def test_rebinding_blocked_live_index_session(dns, server, caplog):
    # LiveIndexSource sends a HEAD request with a session using the live adapter
    sesh = requests.Session()
    sesh.mount('http://', DefaultAdapters.live_adapter)
    dns.hosts['rebind.example.com'] = ['127.0.0.1']

    with pytest.raises(requests.exceptions.ConnectionError):
        sesh.head('http://rebind.example.com:%d/' % server.port)

    assert server.requests == []
    assert_blocked_logged(caplog, 'rebind.example.com')


@pytest.mark.parametrize('host', ['internal.example.com', '127.0.0.1', 'localhost', '[::1]', '0x7f.1', '2130706433'])
def test_blocked_hosts(dns, server, host):
    # the guard doesn't depend on the filter being called first
    with pytest.raises(LiveResourceException):
        live_get('http://%s:%d/' % (host, server.port))

    assert server.requests == []


def test_blocked_error(dns, server, caplog):
    pool = GuardedHTTPConnectionPool('internal.example.com', server.port, retries=False)
    with pytest.raises(NewConnectionError) as e:
        pool.urlopen('GET', '/', retries=False)

    assert 'Blocked by live_url_filter: internal.example.com resolves to a blocked address' in str(e.value)
    assert_blocked_logged(caplog, 'internal.example.com:%d, resolved to 127.0.0.1' % server.port)


def test_blocked_networks(dns, server, redirect):
    LiveUrlFilter.init({'blocked_networks': [PUBLIC_IP]})

    with pytest.raises(LiveResourceException):
        live_get('http://public.example.com:%d/' % server.port)

    assert redirect.addresses == []


# Allowed connections
def test_public_host_connects(dns, server, redirect):
    res = live_get('http://public.example.com:%d/path?q=1' % server.port)
    assert res.status == 200
    assert res.read() == b'INTERNAL SECRET'

    assert redirect.addresses == [PUBLIC_IP]
    # the connection keeps the host name
    assert server.requests[0][1] == '/path?q=1'
    assert server.requests[0][2]['Host'] == 'public.example.com:%d' % server.port


def test_public_host_connects_remote_archive(dns, server, redirect):
    res = live_get('http://public.example.com:%d/web/2020id_/http://example.com/' % server.port, is_live=False)
    assert res.status == 200
    assert redirect.addresses == [PUBLIC_IP]


def test_public_ip_literal_connects(dns, server, redirect):
    res = live_get('http://%s:%d/' % (PUBLIC_IP, server.port))
    assert res.status == 200
    assert redirect.addresses == [PUBLIC_IP]


def test_mixed_addresses_only_public(dns, server, redirect):
    # the first public address refuses the connection, the next public is tried
    redirect.refused = (PUBLIC_IP,)
    res = live_get('http://mixed.example.com:%d/' % server.port)
    assert res.status == 200
    assert redirect.addresses == [PUBLIC_IP, PUBLIC_IP_2]


def test_mixed_addresses_all_public_fail(dns, server, redirect):
    redirect.refused = (PUBLIC_IP, PUBLIC_IP_2, PUBLIC_IPV6)
    conn = GuardedHTTPConnection('mixed.example.com', server.port)
    with pytest.raises(NewConnectionError) as e:
        conn.connect()

    assert 'Failed to establish a new connection' in str(e.value)
    assert redirect.addresses == [PUBLIC_IP, PUBLIC_IP_2, PUBLIC_IPV6]
    assert server.requests == []


def test_connection_options_kept(dns, server, redirect):
    socket_options = [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1), (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
    conn = GuardedHTTPConnection('public.example.com', server.port, timeout=7,
                                 source_address=('127.0.0.1', 0), socket_options=socket_options)
    conn.connect()
    conn.close()

    assert redirect.calls == [((PUBLIC_IP, server.port), 7,
                               {'source_address': ('127.0.0.1', 0), 'socket_options': socket_options})]


def test_connect_timeout(dns):
    with patch('pywb.warcserver.liveconnectguard.create_connection', side_effect=socket.timeout('timed out')):
        conn = GuardedHTTPConnection('public.example.com', 80, timeout=2)
        with pytest.raises(ConnectTimeoutError) as e:
            conn.connect()

    assert 'Connection to public.example.com timed out. (connect timeout=2)' in str(e.value)


def test_host_not_resolved(dns):
    conn = GuardedHTTPConnection('notfound.example.com', 80)
    with pytest.raises(NewConnectionError):
        conn.connect()


def test_https_keeps_host_name(dns, server, redirect):
    # TLS SNI and the certificate host name check use the host name, not the address
    with patch('urllib3.connection.ssl_wrap_socket', side_effect=RuntimeError('stop')) as wrap:
        with pytest.raises(RuntimeError):
            DefaultAdapters.live_adapter.poolmanager.urlopen(
                'GET', 'https://public.example.com:%d/' % server.port, retries=False)

    assert redirect.addresses == [PUBLIC_IP]
    assert wrap.call_args[1]['server_hostname'] == 'public.example.com'

    pool = DefaultAdapters.live_adapter.poolmanager.connection_from_url('https://public.example.com/')
    assert isinstance(pool, GuardedHTTPSConnectionPool)
    assert pool.host == 'public.example.com'


# Requests that must not be affected
def test_remote_index_not_affected(dns, server):
    # a remote cdx server on an internal host, set on the config
    server.body = b'com,example)/ 20200101000000 {"url": "http://example.com/"}\n'
    source = RemoteIndexSource('http://internal.example.com:%d/cdx?url={url}' % server.port,
                               'http://internal.example.com:%d/web/{timestamp}id_/{url}' % server.port)

    res = source.sesh.get('http://internal.example.com:%d/cdx?url=http://example.com/' % server.port)
    assert res.status_code == 200
    assert server.requests[-1][1] == '/cdx?url=http://example.com/'


def test_recorder_localhost_not_affected(dns, server):
    # the recorder and rewriter call the internal warcserver on localhost with requests
    url = 'http://localhost:%d/coll/resource/postreq?param.recorder.coll=coll' % server.port
    res = requests.request('GET', url)
    assert res.status_code == 200
    assert res.content == b'INTERNAL SECRET'

    assert requests.Session().get_adapter(url).poolmanager.pool_classes_by_scheme is pool_classes_by_scheme


def test_http_loader_archive_path_not_affected(dns, server):
    # WARC records loaded from an http:// archive path, on a host resolving to
    # a blocked address, use HttpLoader with its own session
    server.files['/warcs/test.warc.gz'] = b'0123456789WARC RECORD'
    url = 'http://warcs.internal.example.org:%d/warcs/test.warc.gz' % server.port

    assert BlockLoader().load(url, 10, 11).read() == b'WARC RECORD'
    assert server.requests[-1][2]['Range'] == 'bytes=10-20'

    # the same host is blocked for live loads
    with pytest.raises(LiveResourceException):
        live_get(url)


def write_warc(tmp_path):
    warc = BytesIO()
    writer = WARCWriter(warc, gzip=True)
    http_headers = StatusAndHeaders('200 OK', [('Content-Type', 'text/plain')], protocol='HTTP/1.0')
    writer.write_record(writer.create_warc_record('http://example.com/', 'response',
                                                  payload=BytesIO(b'ARCHIVED PAGE'),
                                                  http_headers=http_headers))

    index = tmp_path / 'index.cdxj'
    with open(str(index), 'wb') as out:
        write_cdx_index(out, BytesIO(warc.getvalue()), 'test.warc.gz', cdxj=True)

    return warc.getvalue(), index


def test_warcserver_http_archive_path_not_affected(dns, server, tmp_path):
    warc, index = write_warc(tmp_path)
    server.files['/warcs/test.warc.gz'] = warc

    app = WarcServer(config_file=None, custom_config={
        'collections': {'arc': {
            'index_paths': str(index),
            'archive_paths': 'http://warcs.internal.example.org:%d/warcs/' % server.port,
        }},
        'live_url_filter': {'blocked_domains': ['internal.example.org']},
        'enable_auto_colls': False,
    })

    res = Client(app, Response).get('/arc/resource?url=http://example.com/')

    assert res.status_code == 200
    assert b'ARCHIVED PAGE' in res.data
    assert server.requests[-1][1] == '/warcs/test.warc.gz'
    assert server.requests[-1][2]['Range'].startswith('bytes=0-')
