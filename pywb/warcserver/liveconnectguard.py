import logging
import socket
import sys

from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import ConnectTimeoutError, NewConnectionError
from urllib3.util.connection import allowed_gai_family, create_connection


logger = logging.getLogger('warcserver')


# =============================================================================
class LiveConnectGuard(object):
    """Checks the address pywb connects to, when requesting a url from the
    live web or loading a resource from a remote archive.

    A ``live_url_filter`` that resolves the host is not enough on its own:
    urllib3 resolves the host again when connecting, so a DNS rebinding
    domain (TTL 0, a public address first and an internal one next) gets past
    the filter.

    When installed, the guarded connections resolve the host once, drop the
    addresses rejected by ``is_ip_blocked`` and only connect to an allowed
    one. The host name is kept on the connection, so the ``Host`` header,
    TLS SNI and certificate checks are unchanged.

    It is installed by the built-in live url filter
    (:class:`pywb.warcserver.liveurlfilter.PublicUrlFilter`). Only the
    connections of the adapters created with ``connect_guard=True`` are
    checked, the other requests (remote indexes, WARC records loaded over
    http, the recorder) are not changed.
    """
    is_ip_blocked = None

    @classmethod
    def install(cls, ip_blocked_func):
        """``ip_blocked_func(addr)`` returns True if pywb must not connect to
        the IP address ``addr``."""
        cls.is_ip_blocked = ip_blocked_func

    @classmethod
    def uninstall(cls):
        cls.is_ip_blocked = None


# =============================================================================
class GuardedConnectionMixin(object):
    def _new_conn(self):
        """Same as urllib3 ``HTTPConnection._new_conn``, but only connects to
        the allowed addresses of a single host resolution.
        """
        is_ip_blocked = LiveConnectGuard.is_ip_blocked
        if not is_ip_blocked:
            return super(GuardedConnectionMixin, self)._new_conn()

        extra_kw = {}
        if self.source_address:
            extra_kw['source_address'] = self.source_address

        if self.socket_options:
            extra_kw['socket_options'] = self.socket_options

        try:
            addr_infos = socket.getaddrinfo(self._dns_host.strip('[]'), self.port,
                                            allowed_gai_family(), socket.SOCK_STREAM)
        except (OSError, UnicodeError) as e:
            raise NewConnectionError(self, 'Failed to establish a new connection: %s' % e)

        addresses = []
        for addr_info in addr_infos:
            if addr_info[4][0] not in addresses:
                addresses.append(addr_info[4][0])

        allowed = [addr for addr in addresses if not is_ip_blocked(addr)]
        if not allowed:
            logger.warning('live_url_filter blocked: connection to %s:%s, resolved to %s',
                           self.host, self.port, ', '.join(addresses) or 'no address')
            raise NewConnectionError(self, 'Blocked by live_url_filter: %s resolves to a blocked address'
                                     % self.host)

        err = None
        for addr in allowed:
            try:
                sock = create_connection((addr, self.port), self.timeout, **extra_kw)
            except OSError as e:
                err = e
                continue

            sys.audit('http.client.connect', self, self.host, self.port)
            return sock

        if isinstance(err, socket.timeout):
            raise ConnectTimeoutError(
                self, 'Connection to %s timed out. (connect timeout=%s)' % (self.host, self.timeout))

        raise NewConnectionError(self, 'Failed to establish a new connection: %s' % err)


class GuardedHTTPConnection(GuardedConnectionMixin, HTTPConnection):
    pass


class GuardedHTTPSConnection(GuardedConnectionMixin, HTTPSConnection):
    pass


class GuardedHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = GuardedHTTPConnection


class GuardedHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = GuardedHTTPSConnection


GUARDED_POOL_CLASSES_BY_SCHEME = {
    'http': GuardedHTTPConnectionPool,
    'https': GuardedHTTPSConnectionPool,
}
