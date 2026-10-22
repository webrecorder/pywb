import pytest
from mock import patch

from pywb.warcserver.liveconnectguard import LiveConnectGuard
from pywb.warcserver.liveurlfilter import LiveUrlFilter, PublicUrlFilter

from .liveguardutils import FakeDNS, PUBLIC_IP, PUBLIC_IPV6


ENV_VARS = ('PYWB_LIVE_BLOCKED_DOMAINS', 'PYWB_LIVE_BLOCKED_NETWORKS', 'PYWB_LIVE_CONNECT_GUARD',
            'SOCKS_HOST', 'SOCKS_DISABLE')


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    dns = FakeDNS({
        'public.example.com': [PUBLIC_IP, PUBLIC_IPV6],
        'private.example.com': ['10.1.2.3'],
        'mixed.example.com': [PUBLIC_IP, '127.0.0.1'],
        'archive.example.com': ['93.184.215.20'],
        'internal.example.org': [PUBLIC_IP],
        'www.internal.example.org': [PUBLIC_IP],
        'www.notinternal.example.org': [PUBLIC_IP],
        'internal.example.org.example.com': [PUBLIC_IP],
    })
    with patch('socket.getaddrinfo', dns):
        yield dns

    LiveUrlFilter.init(None)


@pytest.fixture
def is_url_allowed():
    return PublicUrlFilter()


def live_cdx(url):
    return {'url': url, 'load_url': url, 'is_live': 'true'}


@pytest.mark.parametrize('url', [
    'http://public.example.com/',
    'https://public.example.com:8443/path?q=1',
    'http://93.184.215.14/',
    'http://[2606:2800:21f:cb07:6820:80da:af6b:8b2c]/',
    'http://internal.example.org/',
    # NAT64 of a public address
    'http://[64:ff9b::5db8:d70e]/',
])
def test_allowed(is_url_allowed, url):
    assert is_url_allowed(url, live_cdx(url)) is True
    assert is_url_allowed(url) is True


@pytest.mark.parametrize('url', [
    # private, loopback, link-local, cgnat, reserved, unspecified, multicast, documentation
    'http://10.0.0.1/',
    'http://172.16.5.4:8080/',
    'http://192.168.1.1/',
    'http://127.0.0.1:6379/',
    'http://127.1/',
    'http://localhost/',
    'http://169.254.169.254/latest/meta-data/',
    'http://100.64.0.1/',
    'http://0.0.0.0:8080/',
    'http://240.0.0.1/',
    'http://224.0.0.1/',
    'http://192.0.2.1/',
    # alternative IPv4 notations
    'http://2130706433/',
    'http://0x7f000001/',
    'http://0x7f.0.0.1/',
    'http://0177.0.0.1/',
    # IPv6 and IPv4 embedded in IPv6
    'http://[::1]/',
    'http://[::]/',
    'http://[fe80::1]/',
    'http://[fc00::1]/',
    'http://[2001:db8::1]/',
    'http://[::ffff:10.0.0.1]/',
    'http://[::ffff:7f00:1]/',
    'http://[2002:0a00:0001::1]/',
    'http://[64:ff9b::a00:1]/',
    'http://[64:ff9b:1::a00:1]/',
    'http://[::127.0.0.1]/',
    'http://[::10.0.0.1]/',
    'http://[::5db8:d70e]/',
    'http://[::ffff:0:a00:1]/',
    'http://[::ffff:0:5db8:d70e]/',
    'http://[4000::1]/',
    # host names resolving to private addresses
    'http://private.example.com/',
    'http://mixed.example.com/',
    'http://LOCALHOST./',
    # not resolvable, or no host
    'http://does-not-exist.invalid/',
    'http:///path',
    'file:///etc/passwd',
])
def test_blocked(is_url_allowed, url):
    assert is_url_allowed(url, live_cdx(url)) is False


def test_remote_archive_load(is_url_allowed):
    load_url = 'https://archive.example.com/web/2020id_/'

    for orig_url in ['http://public.example.com/', 'http://does-not-exist.invalid/']:
        assert is_url_allowed(load_url + orig_url, {'url': orig_url}) is True

    for orig_url in ['http://10.0.0.1/', 'http://0x7f000001/', 'http://[::1]/']:
        assert is_url_allowed(load_url + orig_url, {'url': orig_url}) is False

    # the original host is not resolved, it is not contacted
    assert is_url_allowed(load_url + 'http://private.example.com/',
                          {'url': 'http://private.example.com/'}) is True

    # the archive host itself must be public
    assert is_url_allowed('http://10.0.0.1/web/2020id_/http://public.example.com/',
                          {'url': 'http://public.example.com/'}) is False


def test_blocked_domains():
    is_url_allowed = PublicUrlFilter({'blocked_domains': ['internal.example.org', '.Other.Example.']})
    assert is_url_allowed.blocked_domains == ['internal.example.org', 'other.example']

    for url in ['http://internal.example.org/', 'https://INTERNAL.example.org./',
                'http://www.internal.example.org:8080/', 'http://user:pass@sub.internal.example.org/',
                # unicode alternative dots
                'http://sub.internal.example。org/',
                'http://other.example/']:
        assert is_url_allowed(url) is False, url

    for url in ['http://www.notinternal.example.org/', 'http://internal.example.org.example.com/']:
        assert is_url_allowed(url) is True, url

    # not resolved, the original url of a remote archive load
    load_url = 'https://archive.example.com/web/2020id_/http://www.internal.example.org/'
    assert is_url_allowed(load_url, {'url': 'http://www.internal.example.org/'}) is False


def test_blocked_networks():
    is_url_allowed = PublicUrlFilter({'blocked_networks': ['93.184.215.0/24', '2606:2800:21f::/48']})

    assert is_url_allowed('http://93.184.215.14/') is False
    assert is_url_allowed('http://public.example.com/') is False
    assert is_url_allowed('http://[2606:2800:21f:cb07::1]/') is False
    assert is_url_allowed('http://[::ffff:93.184.215.14]/') is False
    assert is_url_allowed('http://207.241.237.3/') is True

    # comma separated string, single addresses and non strict networks
    networks = PublicUrlFilter({'blocked_networks': '93.184.215.14, 93.184.215.21/24'}).blocked_networks
    assert [str(network) for network in networks] == ['93.184.215.14/32', '93.184.215.0/24']


def test_env_replaces_config(monkeypatch):
    monkeypatch.setenv('PYWB_LIVE_BLOCKED_DOMAINS', ' internal.example.org , .other.example. ')
    monkeypatch.setenv('PYWB_LIVE_BLOCKED_NETWORKS', '93.184.215.14, 2001:db8::/32')

    is_url_allowed = PublicUrlFilter({'blocked_domains': ['config.example'],
                                      'blocked_networks': ['207.241.237.0/24']})

    assert is_url_allowed.blocked_domains == ['internal.example.org', 'other.example']
    assert [str(network) for network in is_url_allowed.blocked_networks] == ['93.184.215.14/32', '2001:db8::/32']
    assert is_url_allowed('http://93.184.215.14/') is False
    assert is_url_allowed('http://www.other.example/') is False
    assert is_url_allowed('http://config.example/', {'url': 'http://config.example/'}) is False
    assert is_url_allowed('http://207.241.237.3/') is True


def test_env_empty_clears_config(monkeypatch):
    monkeypatch.setenv('PYWB_LIVE_BLOCKED_DOMAINS', '')

    is_url_allowed = PublicUrlFilter({'blocked_domains': ['internal.example.org']})
    assert is_url_allowed.blocked_domains == []
    assert is_url_allowed('http://internal.example.org/') is True


def test_socks_proxy_does_not_resolve(monkeypatch, fake_dns):
    is_url_allowed = PublicUrlFilter({'blocked_domains': 'internal.example.org'})

    monkeypatch.setenv('SOCKS_HOST', 'localhost')

    # the proxy resolves the host names, eg. .onion hosts
    assert is_url_allowed('http://exampleonionaddress.onion/') is True
    assert is_url_allowed('http://private.example.com/') is True
    assert fake_dns.lookups == []

    # IP literals and blocked domains are still checked
    assert is_url_allowed('http://127.0.0.1/') is False
    assert is_url_allowed('http://0x7f.1/') is False
    assert is_url_allowed('http://www.internal.example.org/') is False

    monkeypatch.setenv('SOCKS_DISABLE', '1')
    assert is_url_allowed('http://private.example.com/') is False


# LiveUrlFilter config
@pytest.mark.parametrize('config', [True, {}, {'blocked_domains': ['internal.example.org']}])
def test_init_builtin(config):
    LiveUrlFilter.init(config)

    assert isinstance(LiveUrlFilter.func, PublicUrlFilter)
    assert LiveConnectGuard.is_ip_blocked == LiveUrlFilter.func.is_ip_blocked

    assert LiveUrlFilter.is_allowed('http://public.example.com/') is True
    assert LiveUrlFilter.is_allowed('http://10.0.0.1/') is False


@pytest.mark.parametrize('config', [None, False, ''])
def test_init_disabled(config):
    LiveUrlFilter.init(True)
    LiveUrlFilter.init(config)

    assert LiveUrlFilter.func is None
    assert LiveConnectGuard.is_ip_blocked is None
    assert LiveUrlFilter.is_allowed('http://10.0.0.1/') is True


def test_init_custom_function_no_guard():
    LiveUrlFilter.init(True)
    LiveUrlFilter.init(__name__ + ':live_cdx')

    assert LiveUrlFilter.func == live_cdx
    assert LiveConnectGuard.is_ip_blocked is None


@pytest.mark.parametrize('value', [False, 'false', 'off', '0', 'no'])
def test_init_connect_guard_disabled(value):
    LiveUrlFilter.init({'connect_guard': value})

    assert isinstance(LiveUrlFilter.func, PublicUrlFilter)
    assert LiveConnectGuard.is_ip_blocked is None


@pytest.mark.parametrize('value', ['false', 'False', '0', 'no', 'off'])
def test_init_connect_guard_disabled_by_env(monkeypatch, value):
    monkeypatch.setenv('PYWB_LIVE_CONNECT_GUARD', value)
    LiveUrlFilter.init({'connect_guard': True})

    assert LiveConnectGuard.is_ip_blocked is None


@pytest.mark.parametrize('value', ['true', '1', ''])
def test_init_connect_guard_enabled_by_env(monkeypatch, value):
    monkeypatch.setenv('PYWB_LIVE_CONNECT_GUARD', value)
    LiveUrlFilter.init({'connect_guard': False})

    assert LiveConnectGuard.is_ip_blocked == LiveUrlFilter.func.is_ip_blocked


def test_init_invalid():
    with pytest.raises(TypeError):
        LiveUrlFilter.init(['internal.example.org'])

    with pytest.raises(ValueError):
        LiveUrlFilter.init({'blocked_networks': ['not-a-network']})
