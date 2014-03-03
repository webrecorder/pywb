class WbException(Exception):
    def status(self):
        return '500 Internal Server Error'
