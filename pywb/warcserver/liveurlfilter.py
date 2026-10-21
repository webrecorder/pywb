import ipaddress
import logging
import os
import socket

from urllib3.exceptions import LocationParseError
from urllib3.util import parse_url

from pywb.utils.loaders import load_py_name
from pywb.warcserver.liveconnectguard import LiveConnectGuard


logger = logging.getLogger('warcserver')


# =============================================================================
class LiveUrlFilter(object):
    """Optional hook called before pywb requests a url from the live web or
    from a remote (eg. memento) archive.

    Configured with the top-level ``live_url_filter`` option, set to:

    * a ``module:function`` string, for a custom filter function. It is
      called as ``func(url, cdx)``, where ``url`` is the url about to be
      requested and ``cdx`` is the :class:`CDXObject` being loaded
      (``cdx['url']`` is the original url, ``cdx.get('is_live')`` is set for
      live web loads). It must return ``True`` if the request is allowed.
    * ``true`` or a dict of options, for the built-in
      :class:`PublicUrlFilter`.

    If the function raises an exception, the request is not allowed.
    """
    func = None

    @classmethod
    def init(cls, config):
        LiveConnectGuard.uninstall()

        if config is True or isinstance(config, dict):
            cls.func = PublicUrlFilter(config if isinstance(config, dict) else {})
            if cls.func.connect_guard:
                LiveConnectGuard.install(cls.func.is_ip_blocked)
        elif not config:
            cls.func = None
        elif isinstance(config, str):
            cls.func = load_py_name(config)
        else:
            raise TypeError('live_url_filter must be a "module:function" string, true or a dict')

    @classmethod
    def is_allowed(cls, url, cdx=None):
        if not cls.func:
            return True

        try:
            allowed = bool(cls.func(url, cdx))
        except Exception:
            logger.exception('live_url_filter failed for: ' + str(url))
            allowed = False

        if not allowed:
            logger.warning('live_url_filter blocked: ' + str(url))

        return allowed


# =============================================================================
class PublicUrlFilter(object):
    """Built-in live url filter, only allows requests to public hosts.

    A url is blocked if its host:

    * does not resolve, or any of its addresses is not public (private
      networks, loopback, link-local, carrier-grade NAT, reserved, multicast,
      ...), including the IPv6 forms that embed one of those IPv4 addresses;
    * is in ``blocked_domains``, or is a subdomain of one of them;
    * has any address in ``blocked_networks``.

    When loading from a remote archive, ``url`` is the archive url, its host
    is checked as above. The original url (``cdx['url']``) is not requested,
    so its host is not resolved, only blocked domains and IP literals are
    checked.

    When a SOCKS proxy is used, the proxy resolves the host names, so they
    are not resolved by the filter either.

    Options, the environment variables replace the config values when set:

    * ``blocked_domains`` (``PYWB_LIVE_BLOCKED_DOMAINS``): list of domains,
      or a comma separated string;
    * ``blocked_networks`` (``PYWB_LIVE_BLOCKED_NETWORKS``): list of IP
      addresses or networks (CIDR), or a comma separated string;
    * ``connect_guard`` (``PYWB_LIVE_CONNECT_GUARD``): install the
      :class:`pywb.warcserver.liveconnectguard.LiveConnectGuard`, which
      checks the address again when connecting, against DNS rebinding.
      Enabled by default.
    """
    NAT64_NETWORK = ipaddress.ip_network('64:ff9b::/96')

    FALSE_VALUES = ('false', '0', 'no', 'off')

    def __init__(self, config=None):
        config = config or {}

        self.blocked_domains = [self._normalize_host(domain.strip('.')) for domain in
                                self._get_list(config, 'blocked_domains', 'PYWB_LIVE_BLOCKED_DOMAINS')]

        self.blocked_networks = [ipaddress.ip_network(network, strict=False) for network in
                                 self._get_list(config, 'blocked_networks', 'PYWB_LIVE_BLOCKED_NETWORKS')]

        connect_guard = os.environ.get('PYWB_LIVE_CONNECT_GUARD')
        if connect_guard is None:
            connect_guard = config.get('connect_guard', True)
        if isinstance(connect_guard, str):
            connect_guard = connect_guard.strip().lower() not in self.FALSE_VALUES
        self.connect_guard = bool(connect_guard)

    @staticmethod
    def _get_list(config, name, env_name):
        values = os.environ.get(env_name)
        if values is None:
            values = config.get(name) or []

        if isinstance(values, str):
            values = values.split(',')

        return [str(value).strip() for value in values if str(value).strip()]

    def __call__(self, url, cdx=None):
        """Return True if pywb is allowed to request ``url``."""
        resolve = not self._is_socks_proxy_enabled()

        if not self._is_host_allowed(self._get_host(url), resolve=resolve):
            return False

        orig_url = cdx.get('url') if cdx else None
        if orig_url and orig_url != url:
            return self._is_host_allowed(self._get_host(orig_url), resolve=False)

        return True

    @staticmethod
    def _is_socks_proxy_enabled():
        # same check as LiveWebLoader
        return bool(os.environ.get('SOCKS_HOST') and not os.environ.get('SOCKS_DISABLE'))

    @staticmethod
    def _normalize_host(host):
        host = host.strip('[]').rstrip('.').lower()
        try:
            # normalize unicode hosts, eg. alternative dots
            host = host.encode('idna').decode('ascii')
        except UnicodeError:
            pass

        return host

    def _get_host(self, url):
        # parse with urllib3, the same parser used to connect
        try:
            host = parse_url(url).host
        except LocationParseError:
            return None

        if not host:
            return None

        return self._normalize_host(host)

    def _is_host_allowed(self, host, resolve):
        if not host:
            return False

        if any(host == domain or host.endswith('.' + domain) for domain in self.blocked_domains):
            return False

        # without resolve, only parse IP literals (including forms like 0x7f.1 or 2130706433)
        flags = 0 if resolve else socket.AI_NUMERICHOST
        try:
            addr_infos = socket.getaddrinfo(host, None, 0, socket.SOCK_STREAM, 0, flags)
        except (OSError, UnicodeError, ValueError):
            # can't connect to a host that does not resolve,
            # when not resolving, it is a host name and not an IP literal
            return not resolve

        return not any(self.is_ip_blocked(addr_info[4][0]) for addr_info in addr_infos)

    def is_ip_blocked(self, addr):
        """Return True if ``addr`` is not a public IP address, or is in
        ``blocked_networks``."""
        ip = ipaddress.ip_address(addr.split('%', 1)[0])

        if ip.version == 6:
            embedded = ip.ipv4_mapped or ip.sixtofour or (ip.teredo and ip.teredo[1])
            if not embedded and ip in self.NAT64_NETWORK:
                embedded = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
            if embedded and self.is_ip_blocked(str(embedded)):
                return True

        if not ip.is_global or ip.is_multicast:
            return True

        # is_global is True for some reserved IPv6 forms that embed an IPv4
        # address, like the deprecated IPv4-compatible ::a.b.c.d or the
        # IPv4-translated ::ffff:0:a.b.c.d, the NAT64 embedded address was checked
        if ip.is_reserved and ip not in self.NAT64_NETWORK:
            return True

        return any(ip in network for network in self.blocked_networks)
