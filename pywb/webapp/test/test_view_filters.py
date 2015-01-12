"""
>>> format_ts('20141226101000')
'Fri, Dec 26 2014 10:10:00'

>>> format_ts('20141226101000', '%s')
1419588600

>>> is_wb_handler(DebugEchoHandler())
False


"""

from pywb.webapp.views import format_ts, is_wb_handler
from pywb.webapp.handlers import DebugEchoHandler


if __name__ == "__main__":
    import doctest
    doctest.testmod()
