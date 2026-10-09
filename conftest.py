import ipaddress
import socket
import sys

import pytest


# ============================================================================
# Tests must not reach the live web: it makes them flaky, and they break when
# a remote site changes. Use a local server (e.g. HttpBinLiveTests, GeventServer)
# or a mock instead.
#
# Tests that really need the network must be marked with @pytest.mark.live;
# they are skipped unless pytest is run with --live.
#
# Every other test is blocked from resolving or connecting to any host except
# loopback, and fails if it tries to. Hosts under the reserved .invalid TLD
# (RFC 6761) never resolve, so they fail to resolve without reaching DNS.

class LiveWebBlocked(OSError):
    pass


class _State(object):
    allow = False
    hits = []


def _host_str(host):
    return host.decode('utf-8', 'replace') if isinstance(host, bytes) else str(host)


def _is_local(host):
    if host in ('', 'localhost') or host.endswith('.localhost'):
        return True

    try:
        ip = ipaddress.ip_address(host.split('%')[0])
        return ip.is_loopback or ip.is_unspecified
    except ValueError:
        return False


def _block_live_web(event, args):
    if event == 'socket.getaddrinfo':
        host = args[0]
    elif event == 'socket.connect':
        addr = args[1]
        # AF_UNIX and other non-inet addresses
        if not isinstance(addr, tuple) or not addr:
            return
        host = addr[0]
    else:
        return

    if host is None:
        return

    host = _host_str(host).rstrip('.').lower()
    if _is_local(host):
        return

    if host == 'invalid' or host.endswith('.invalid'):
        raise socket.gaierror(socket.EAI_NONAME, 'Name or service not known')

    if _State.allow:
        return

    _State.hits.append(host)
    raise LiveWebBlocked('live web access blocked in tests: ' + host)


sys.addaudithook(_block_live_web)


# ============================================================================
def pytest_addoption(parser):
    parser.addoption('--live', action='store_true', default=False,
                     help='run tests marked as live, which reach the live web')


def pytest_configure(config):
    config.addinivalue_line('markers', 'live: test reaches the live web, skipped unless --live is given')


def pytest_collection_modifyitems(config, items):
    if config.getoption('--live'):
        return

    skip_live = pytest.mark.skip(reason='reaches the live web, use --live to run')
    for item in items:
        if item.get_closest_marker('live'):
            item.add_marker(skip_live)


@pytest.fixture(autouse=True)
def block_live_web(request):
    _State.allow = request.node.get_closest_marker('live') is not None
    yield
    _State.allow = False

    # also reports hits from class setup, which runs before this fixture
    hits = sorted(set(_State.hits))
    del _State.hits[:]
    if hits:
        pytest.fail('test tried to reach the live web: {0}. Use a local server '
                    'or a mock, or mark it with @pytest.mark.live'.format(', '.join(hits)),
                    pytrace=False)
