
class WbException(Exception):
    pass

class NotFoundException(WbException):
    def status(_):
        return '404 Not Found'

# Exceptions that effect a specific capture and result in a retry
class CaptureException(WbException):
    def status(_):
        return '500 Internal Server Error'

class InternalRedirect(WbException):
    def __init__(self, location, status = '302 Internal Redirect'):
        WbException.__init__(self, 'Redirecting -> ' + location)
        self.status = status
        self.httpHeaders = [('Location', location)]

    def status(self):
        return self.status

