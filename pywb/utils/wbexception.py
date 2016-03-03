

#=================================================================
class WbException(Exception):
    def __init__(self, msg=None, url=None):
        Exception.__init__(self, msg)
        self.msg = msg
        self.url = url

# Default Error Code
#    def status(self):
#        return '500 Internal Server Error'


#=================================================================
class AccessException(WbException):
    def status(self):
        return '403 Access Denied'


#=================================================================
class BadRequestException(WbException):
    def status(self):
        return '400 Bad Request'


#=================================================================
class NotFoundException(WbException):
    def status(self):
        return '404 Not Found'


#=================================================================
class LiveResourceException(WbException):
    def status(self):
        return '400 Bad Live Resource'


