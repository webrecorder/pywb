from pywb.utils.wbexception import WbException


# Exceptions that effect a specific capture and result in a retry
class CaptureException(WbException):
    def status(self):
        return '502 Internal Server Error'

