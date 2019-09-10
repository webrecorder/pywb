from werkzeug.http import HTTP_STATUS_CODES


# =================================================================
class WbException(Exception):
    """Base class for exceptions raised by Pywb"""

    def __init__(self, msg=None, url=None):
        """Initialize a new WbException

        :param str|dict|None msg: The message for the error response
        :param str|None url: The URL that caused the error
        :rtype: None
        """
        super(WbException, self).__init__(msg)
        self.msg = msg
        self.url = url

    @property
    def status_code(self):
        """Returns the status code to be used for the error response

        :return: The status code for the error response (500)
        :rtype: int
        """
        return 500

    def status(self):
        """Returns the HTTP status line for the error response

        :return: The HTTP status line for the error response
        :rtype: str
        """
        return str(self.status_code) + ' ' + HTTP_STATUS_CODES.get(self.status_code, 'Unknown Error')

    def __repr__(self):
        return "{0}('{1}',)".format(self.__class__.__name__, self.msg)


# =================================================================
class AccessException(WbException):
    """An Exception used to indicate an access control violation"""

    @property
    def status_code(self):
        """Returns the status code to be used for the error response

        :return: The status code for the error response (451)
        :rtype: int
        """
        return 451


# =================================================================
class BadRequestException(WbException):
    """An Exception used to indicate that request was bad"""

    @property
    def status_code(self):
        """Returns the status code to be used for the error response

        :return: The status code for the error response (400)
        :rtype: int
        """
        return 400


# =================================================================
class NotFoundException(WbException):
    """An Exception used to indicate that a resource was not found"""

    @property
    def status_code(self):
        """Returns the status code to be used for the error response

        :return: The status code for the error response (404)
        :rtype: int
        """
        return 404


# =================================================================
class LiveResourceException(WbException):
    """An Exception used to indicate that an error was encountered during the
    retrial of a live web resource"""

    @property
    def status_code(self):
        """Returns the status code to be used for the error response

        :return: The status code for the error response (400)
        :rtype: int
        """
        return 400


# ============================================================================
class UpstreamException(WbException):
    """An Exception used to indicate that an error was encountered from an upstream endpoint"""

    def __init__(self, status_code, url, details):
        """Initialize a new UpstreamException

        :param int status_code: The status code for the error response
        :param str url: The URL that caused the error
        :param str|dict details: The details of the error encountered
        :rtype: None
        """
        super(UpstreamException, self).__init__(url=url, msg=details)
        self._status_code = status_code

    @property
    def status_code(self):
        """Returns the status code to be used for the error response

        :return: The status code for the error response
        :rtype: int
        """
        return self._status_code


# ============================================================================
class AppPageNotFound(WbException):
    """An Exception used to indicate that a page was not found"""

    @property
    def status_code(self):
        """Returns the status code to be used for the error response

        :return: The status code for the error response (400)
        :rtype: int
        """
        return 404
