
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
    def __init__(msg, errList = None):
        super(InvalidArchiveRecordException, self).__init__(msg)
        self.errList = errList


