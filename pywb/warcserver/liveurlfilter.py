import logging

from pywb.utils.loaders import load_py_name


logger = logging.getLogger('warcserver')


# =============================================================================
class LiveUrlFilter(object):
    """Optional hook called before pywb requests a url from the live web or
    from a remote (eg. memento) archive.

    Configured with the top-level ``live_url_filter`` option, set to a
    ``module:function`` string. The function is called as ``func(url, cdx)``,
    where ``url`` is the url about to be requested and ``cdx`` is the
    :class:`CDXObject` being loaded (``cdx['url']`` is the original url,
    ``cdx.get('is_live')`` is set for live web loads).
    It must return ``True`` if the request is allowed.

    If the function raises an exception, the request is not allowed.
    """
    func = None

    @classmethod
    def init(cls, name):
        cls.func = load_py_name(name) if name else None

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
