
class RequestParseException(Exception):
    def status(_):
        return '400 Bad Request'

class BadUrlException(Exception):
    def status(_):
        return '400 Bad Request'

class AccessException(Exception):
    def status(_):
        return '403 Forbidden'

class InvalidCDXException(Exception):
    def status(_):
        return '500 Internal Server Error'

class NotFoundException(Exception):
    def status(_):
        return '404 Not Found'

# Exceptions that effect a specific capture and result in a retry
class CaptureException(Exception):
    def status(_):
        return '500 Internal Server Error'

class UnresolvedArchiveFileException(CaptureException):
    pass

class UnknownArchiveFormatException(CaptureException):
    pass

class UnknownLoaderProtocolException(CaptureException):
    pass

class InvalidArchiveRecordException(CaptureException):
    def __init__(self, msg, errList = None):
        super(InvalidArchiveRecordException, self).__init__(msg)
        self.errList = errList

class ArchiveLoadFailed(CaptureException):
    def __init__(self, filename, reason):
        super(ArchiveLoadFailed, self).__init__(filename + ':' + str(reason))
        self.filename = filename
        self.reason = reason

    def status(_):
        return '503 Service Unavailable'

class InternalRedirect(Exception):
    def __init__(self, location, status = '302 Internal Redirect'):
        Exception.__init__(self, 'Redirecting -> ' + location)
        self.status = status
        self.httpHeaders = [('Location', location)]

    def status(self):
        return self.status

