from pywb.framework.wbrequestresponse import WbResponse
from warcio.statusandheaders import StatusAndHeaders


def test_resp_1():
    resp = vars(WbResponse.text_response('Test'))

    expected = {'body': [b'Test'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '200 OK',
                headers = [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', '4')])}

    assert(resp == expected)


def test_resp_2():
    resp = vars(WbResponse.bin_stream([b'Test', b'Another'], content_type='text/plain; charset=utf-8', status='404'))

    expected = {'body': [b'Test', b'Another'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '404',
                headers = [('Content-Type', 'text/plain; charset=utf-8')])}

    assert(resp == expected)

def test_resp_3():

    resp = vars(WbResponse.redir_response('http://example.com/otherfile'))

    expected = {'body': [], 'status_headers': StatusAndHeaders(protocol = '', statusline = '302 Redirect',
                 headers = [('Location', 'http://example.com/otherfile'), ('Content-Length', '0')])}

    assert(resp == expected)

def test_resp_4():
    resp = vars(WbResponse.text_response('Test').add_range(10, 4, 100))

    expected = {'body': [b'Test'], 'status_headers': StatusAndHeaders(protocol = '', statusline = '206 Partial Content',
                headers = [ ('Content-Type', 'text/plain; charset=utf-8'),
                  ('Content-Length', '4'),
                  ('Content-Range', 'bytes 10-13/100'),
                  ('Accept-Ranges', 'bytes')])}

    assert(resp == expected)


if __name__ == "__main__":
    import doctest
    doctest.testmod()

