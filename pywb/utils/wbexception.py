

#=================================================================
class WbException(Exception):
    def status(self):
        return '500 Internal Server Error'


#=================================================================
class AccessException(WbException):
    def status(self):
        return '403 Access Denied'
