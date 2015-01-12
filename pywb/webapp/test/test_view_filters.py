"""
>>> format_ts('201412261010')
'Fri, Dec 26 2014 10:10:59'

>>> format_ts('201412261010', '%s')
1419617459000

>>> is_wb_handler(DebugEchoHandler())
False


"""

from pywb.webapp.views import format_ts, is_wb_handler
from pywb.webapp.handlers import DebugEchoHandler


if __name__ == "__main__":
    import doctest
    doctest.testmod()
