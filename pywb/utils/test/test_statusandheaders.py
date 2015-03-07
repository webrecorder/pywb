"""
>>> st1 = StatusAndHeadersParser(['HTTP/1.0']).parse(BytesIO(status_headers_1))
>>> st1
StatusAndHeaders(protocol = 'HTTP/1.0', statusline = '200 OK', headers = [ ('Content-Type', 'ABC'),
  ('Some', 'Value'),
  ('Multi-Line', 'Value1    Also This')])

# add range
>>> StatusAndHeaders(statusline = '200 OK', headers=[('Content-Type', 'text/plain')]).add_range(10, 4, 100)
StatusAndHeaders(protocol = '', statusline = '206 Partial Content', headers = [ ('Content-Type', 'text/plain'),
  ('Content-Range', 'bytes 10-13/100'),
  ('Accept-Ranges', 'bytes')])

>>> StatusAndHeadersParser(['Other']).parse(BytesIO(status_headers_1))
Traceback (most recent call last):
StatusAndHeadersParserException: Expected Status Line starting with ['Other'] - Found: HTTP/1.0 200 OK

# test equality op
>>> st1 == StatusAndHeadersParser(['HTTP/1.0']).parse(BytesIO(status_headers_1))
True

# replace header, print new headers
>>> st1.replace_header('some', 'Another-Value'); st1
'Value'
StatusAndHeaders(protocol = 'HTTP/1.0', statusline = '200 OK', headers = [ ('Content-Type', 'ABC'),
  ('Some', 'Another-Value'),
  ('Multi-Line', 'Value1    Also This')])


# remove header
>>> st1.remove_header('some')
True

# already removed
>>> st1.remove_header('Some')
False

# empty
>>> st2 = StatusAndHeadersParser(['HTTP/1.0']).parse(BytesIO(status_headers_2)); x = st2.validate_statusline('204 No Content'); st2
StatusAndHeaders(protocol = '', statusline = '204 No Content', headers = [])


>>> StatusAndHeadersParser(['HTTP/1.0']).parse(BytesIO(status_headers_3))
StatusAndHeaders(protocol = 'HTTP/1.0', statusline = '204 Empty', headers = [('Content-Type', 'Value'), ('Content-Length', '0')])

# case-insensitive match
>>> StatusAndHeadersParser(['HTTP/1.0']).parse(BytesIO(status_headers_4))
StatusAndHeaders(protocol = 'HTTP/1.0', statusline = '204 empty', headers = [('Content-Type', 'Value'), ('Content-Length', '0')])


"""


from pywb.utils.statusandheaders import StatusAndHeadersParser, StatusAndHeaders
from io import BytesIO


status_headers_1 = "\
HTTP/1.0 200 OK\r\n\
Content-Type: ABC\r\n\
HTTP/1.0 200 OK\r\n\
Some: Value\r\n\
Multi-Line: Value1\r\n\
    Also This\r\n\
\r\n\
Body"


status_headers_2 = """

"""

status_headers_3 = "\
HTTP/1.0 204 Empty\r\n\
Content-Type: Value\r\n\
%Invalid%\r\n\
\tMultiline\r\n\
Content-Length: 0\r\n\
\r\n"

status_headers_4 = "\
http/1.0 204 empty\r\n\
Content-Type: Value\r\n\
%Invalid%\r\n\
\tMultiline\r\n\
Content-Length: 0\r\n\
\r\n"


if __name__ == "__main__":
    import doctest
    doctest.testmod()
