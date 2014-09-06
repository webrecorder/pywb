from pywb.rewrite.wburl import WbUrl


#=================================================================
class BaseHandler(object):
    """
    Represents a base handler class that handles any request
    """
    def __call__(self, wbrequest):  # pragma: no cover
        raise NotImplementedError('Need to implement in derived class')

    def get_wburl_type(self):
        return None


#=================================================================
class WbUrlHandler(BaseHandler):
    """
    Represents a handler which assumes the request contains a WbUrl
    Ensure that the WbUrl is parsed in the request
    """
    def get_wburl_type(self):
        return WbUrl
