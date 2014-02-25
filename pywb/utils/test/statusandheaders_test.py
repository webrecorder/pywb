"""
>>> StatusAndHeadersParser(['HTTP/1.0']).parse(StringIO.StringIO(status_headers_1))
StatusAndHeaders(protocol = 'HTTP/1.0', statusline = '200 OK', headers = [ ('Content-Type', 'ABC'),
  ('Some', 'Value'),
  ('Multi-Line', 'Value1    Also This')])

>>> StatusAndHeadersParser(['Other']).parse(StringIO.StringIO(status_headers_1))
Traceback (most recent call last):
StatusAndHeadersParserException: Expected Status Line starting with ['Other'] - Found: HTTP/1.0 200 OK
"""


from pywb.utils.statusandheaders import StatusAndHeadersParser
import StringIO


status_headers_1 = "\
HTTP/1.0 200 OK\r\n\
Content-Type: ABC\r\n\
Some: Value\r\n\
Multi-Line: Value1\r\n\
    Also This\r\n\
\r\n\
Body"


if __name__ == "__main__":
    import doctest
    doctest.testmod()
