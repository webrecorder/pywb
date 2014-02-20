

#=================================================================
class AllowAllPerms:
    """
    Sample Perm Checker which allows all
    """
    def allow_url_lookup(self, urlkey, url):
        """
        Return true/false if url or urlkey (canonicalized url)
        should be allowed
        """
        return True

    def allow_capture(self, cdx):
        """
        Return true/false is specified capture (cdx) should be
        allowed
        """
        return True

    def filter_fields(self, cdx):
        """
        Filter out any forbidden cdx fields from cdx dictionary
        """
        return cdx


#=================================================================
#TODO: other types of perm handlers
