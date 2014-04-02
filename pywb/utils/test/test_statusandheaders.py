"""
>>> st1 = StatusAndHeadersParser(['HTTP/1.0']).parse(BytesIO(status_headers_1))
>>> st1
StatusAndHeaders(protocol = 'HTTP/1.0', statusline = '200 OK', headers = [ ('Content-Type', 'ABC'),
  ('Some', 'Value'),
  ('Multi-Line', 'Value1    Also This')])

>>> StatusAndHeadersParser(['Other']).parse(BytesIO(status_headers_1))
Traceback (most recent call last):
StatusAndHeadersParserException: Expected Status Line starting with ['Other'] - Found: HTTP/1.0 200 OK

# test equality op
>>> st1 == StatusAndHeadersParser(['HTTP/1.0']).parse(BytesIO(status_headers_1))
True

# remove header
>>> st1.remove_header('some')
True

# already removed
>>> st1.remove_header('Some')
False
"""


from pywb.utils.statusandheaders import StatusAndHeadersParser
from io import BytesIO


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
