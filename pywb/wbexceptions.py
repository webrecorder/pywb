
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
