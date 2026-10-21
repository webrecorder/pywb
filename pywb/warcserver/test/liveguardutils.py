"""Helpers for the live url filter and connect guard tests: a fake DNS and a
local http server, standing in for both internal services and public hosts.
"""
import ipaddress
import socket

from pywb.utils.geventserver import GeventServer


REAL_GETADDRINFO = socket.getaddrinfo

PUBLIC_IP = '93.184.215.14'
PUBLIC_IP_2 = '93.184.215.15'
PUBLIC_IPV6 = '2606:2800:21f:cb07:6820:80da:af6b:8b2c'


def addr_infos(ips, port, type=socket.SOCK_STREAM, proto=0):
    return [(socket.AF_INET6 if ':' in ip else socket.AF_INET, type or socket.SOCK_STREAM, proto, '',
             (ip, port or 0, 0, 0) if ':' in ip else (ip, port or 0))
            for ip in ips]


def parse_ip_literal(host):
    """IP literal parsed as ``getaddrinfo`` would, including the IPv4 forms
    like ``0x7f.1`` or ``2130706433``, without calling it: the tests must not
    resolve any non loopback host"""
    try:
        return str(ipaddress.ip_address(host.split('%', 1)[0]))
    except ValueError:
        pass

    try:
        return socket.inet_ntoa(socket.inet_aton(host))
    except (OSError, UnicodeError, ValueError):
        return None


# ============================================================================
class FakeDNS(object):
    """``socket.getaddrinfo`` replacement.

    ``hosts`` maps a host name to its addresses, or to a list of answers,
    one per lookup (the last one is repeated), like a DNS rebinding domain
    with TTL 0. IP literals are parsed, ``localhost`` uses the real resolver
    and other hosts do not resolve.
    """
    def __init__(self, hosts):
        self.hosts = hosts
        self.lookups = []

    def __call__(self, host, port, family=0, type=0, proto=0, flags=0):
        ip = parse_ip_literal(host)
        if ip:
            return addr_infos([ip], port, type, proto)

        if host == 'localhost':
            return REAL_GETADDRINFO(host, port, family, type, proto, flags)

        if host not in self.hosts or flags & socket.AI_NUMERICHOST:
            raise socket.gaierror(socket.EAI_NONAME, 'Name or service not known')

        answers = self.hosts[host]
        if answers and isinstance(answers[0], list):
            ips = answers[min(len(self.lookups_for(host)), len(answers) - 1)]
        else:
            ips = answers

        self.lookups.append((host, ips))
        return addr_infos(ips, port, type, proto)

    def lookups_for(self, host):
        return [ips for name, ips in self.lookups if name == host]


# ============================================================================
class RedirectConnections(object):
    """``create_connection`` replacement for the guard module: records the
    address the guard connects to and connects to the local server instead,
    so connections to "public" addresses can be tested without network."""
    def __init__(self, local_port, create_connection, refused=()):
        self.local_port = local_port
        self.create_connection = create_connection
        self.refused = refused
        self.calls = []

    def __call__(self, address, timeout=None, **kwargs):
        self.calls.append((address, timeout, kwargs))
        if address[0] in self.refused:
            raise ConnectionRefusedError('refused: %s' % address[0])
        return self.create_connection(('127.0.0.1', self.local_port), timeout, **kwargs)

    @property
    def addresses(self):
        return [address[0] for address, timeout, kwargs in self.calls]


# ============================================================================
class LocalServer(object):
    """http server on localhost, ``files`` maps a path to its content,
    served with Range support, other paths return ``body``."""
    def __init__(self, body=b'INTERNAL SECRET', files=None):
        self.body = body
        self.files = files or {}
        self.requests = []
        self.server = None

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        if environ.get('QUERY_STRING'):
            path += '?' + environ['QUERY_STRING']

        headers = dict((name[5:].replace('_', '-').title(), value)
                       for name, value in environ.items() if name.startswith('HTTP_'))
        self.requests.append((environ['REQUEST_METHOD'], path, headers))

        content = self.files.get(environ['PATH_INFO'], self.body)
        status = '200 OK'
        range_header = environ.get('HTTP_RANGE')
        if range_header:
            start, end = range_header.split('=', 1)[1].split('-')
            end = int(end) if end else len(content) - 1
            content = content[int(start):end + 1]
            status = '206 Partial Content'

        start_response(status, [('Content-Type', 'text/plain'),
                                 ('Content-Length', str(len(content)))])
        return [content]

    @property
    def port(self):
        return self.server.port

    def __enter__(self):
        self.server = GeventServer(self, hostname='127.0.0.1')
        return self

    def __exit__(self, *args):
        self.server.stop()
