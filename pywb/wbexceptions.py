
class RequestParseException(Exception):
    def status(_):
        return '400'

class BadUrlException(Exception):
    def status(_):
        return '400'

class AccessException(Exception):
    def status(_):
        return '403'

class InvalidCDXException(Exception):
    def status(_):
        return '500'

class NotFoundException(Exception):
    def status(_):
        return '404'

# Exceptions that effect a specific capture and result in a retry
class CaptureException(Exception):
    def status(_):
        return '500'

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
        return '503'

class InternalRedirect(Exception):
    def __init__(self, location, status = '302 Internal Redirect'):
        Exception.__init__(self, 'Redirecting -> ' + location)
        self.status = status
        self.httpHeaders = [('Location', location)]

    def status(_):
        return self.status

