from pywb.utils.wbexception import WbException


class NotFoundException(WbException):
    def status(self):
        return '404 Not Found'


# Exceptions that effect a specific capture and result in a retry
class CaptureException(WbException):
    def status(self):
        return '502 Internal Server Error'


class InternalRedirect(WbException):
    def __init__(self, location, status='302 Internal Redirect'):
        WbException.__init__(self, 'Redirecting -> ' + location)
        self.status = status
        self.httpHeaders = [('Location', location)]

    def status(self):
        return self.status
