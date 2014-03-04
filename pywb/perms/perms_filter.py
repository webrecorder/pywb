from pywb.utils.wbexception import AccessException


#=================================================================
def create_filter_op(perms_checker):

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
class AllowAllPermsPolicy(object):
    def create_perms_filter_op(self, wbrequest):
        return create_filter_op(self.create_perms_checker(wbrequest))

    def create_perms_checker(self, wbrequest):
        return AllowAllPerms()


#=================================================================
class AllowAllPerms(object):
    """
    Sample Perm Checker which allows all
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
