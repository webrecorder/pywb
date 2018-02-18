from werkzeug.http import HTTP_STATUS_CODES


#=================================================================
class WbException(Exception):
    def __init__(self, msg=None, url=None):
        Exception.__init__(self, msg)
        self.msg = msg
        self.url = url

    @property
    def status_code(self):
        return 500

    def status(self):
        return str(self.status_code) + ' ' + HTTP_STATUS_CODES.get(self.status_code, 'Unknown Error')


#=================================================================
class AccessException(WbException):
    @property
    def status_code(self):
        return 451


#=================================================================
class BadRequestException(WbException):
    @property
    def status_code(self):
        return 400


#=================================================================
class NotFoundException(WbException):
    @property
    def status_code(self):
        return 404


#=================================================================
class LiveResourceException(WbException):
    @property
    def status_code(self):
        return 400

