from pywb.utils.wbexception import AccessException


#=================================================================
def make_perms_cdx_filter(perms_policy, wbrequest):
    """
    Called internally to convert a perms_policy and a request
    to a filter which can be applied on the cdx
    """
    perms_checker = perms_policy(wbrequest)
    if not perms_checker:
        return None

    return _create_cdx_perms_filter(perms_checker)


#=================================================================
def _create_cdx_perms_filter(perms_checker):
    """
    Return a function which will filter the cdx given
    a Perms object.
    :param perms_checker: a Perms object which implements the
        allow_url_lookup() and access_check_capture() methods
    """

    def perms_filter_op(cdx_iter, query):
        """
        filter out those cdx records that user doesn't have access to,
        by consulting :param perms_checker:.
        :param cdx_iter: cdx record source iterable
        :param query: request parameters (CDXQuery)
        :param perms_checker: object implementing permission checker
        """
        if not perms_checker.allow_url_lookup(query.key):
            if query.is_exact:
                raise AccessException('Excluded')

        for cdx in cdx_iter:
            cdx = perms_checker.access_check_capture(cdx)
            if cdx:
                yield cdx

    return perms_filter_op


#================================================================
def allow_all_perms_policy(wbrequest):
    """
    Perms policy which always returns a default Perms object
    which allows everything.

    The perms object is created per request and may store request
    state, if necessary.

    The same perms object may be called with multiple queries
    (such as for each cdx line) per request.
    """
    return Perms()


#=================================================================
class Perms(object):
    """
    A base perms checker which allows everything
    """

    def allow_url_lookup(self, key):
        """
        Return true/false if urlkey (canonicalized url)
        should be allowed.

        Default: allow all
        """
        return True

    def access_check_capture(self, cdx):
        """
        Allow/deny specified cdx capture (dict) to be included
        in the result.
        Return None to reject, or modify the cdx to exclude
        any fields that need to be restricted.

        Default: allow cdx line without modifications
        """
        return cdx
