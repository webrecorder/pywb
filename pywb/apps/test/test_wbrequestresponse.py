import inspect
try:
    import ujson as json
except ImportError:  # pragma: no cover
    import json

from pywb.apps.wbrequestresponse import WbResponse
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


def test_wbresponse_redir_supplied_headers():
    res = WbResponse.redir_response('http://overhere.now', headers=[('A', 'B')])
    assert ('A', 'B') in res.status_headers.headers


def test_wbresponse_creation_defaults():
    res = WbResponse(None)
    assert res.status_headers is None
    assert isinstance(res.body, list)
    assert len(res.body) == 0


def test_wbresponse_encode_stream():
    stream = [u'\u00c3']  # Unicode Character 'LATIN CAPITAL LETTER A WITH TILDE' (U+00C3)
    expected = [b'\xc3\x83']
    encoding_stream = WbResponse.encode_stream(stream)
    assert inspect.isgenerator(encoding_stream)
    assert list(encoding_stream) == expected


def test_wbresponse_text_stream():
    stream = [u'\u00c3']  # Unicode Character 'LATIN CAPITAL LETTER A WITH TILDE' (U+00C3)
    expected = [b'\xc3\x83']
    res = WbResponse.text_stream(stream, content_type='text/plain')
    status_headers = res.status_headers
    assert status_headers.statusline == '200 OK'
    assert ('Content-Type', 'text/plain; charset=utf-8') in status_headers.headers
    assert inspect.isgenerator(res.body)
    assert list(res.body) == expected

    res = WbResponse.text_stream(stream)
    status_headers = res.status_headers
    assert status_headers.statusline == '200 OK'
    assert ('Content-Type', 'text/plain; charset=utf-8') in status_headers.headers
    assert inspect.isgenerator(res.body)
    assert list(res.body) == expected


def test_wbresponse_options_response():
    res = WbResponse.options_response(dict(HTTP_ORIGIN='http://example.com'))
    assert ('Access-Control-Allow-Origin', 'http://example.com') in res.status_headers.headers
    res = WbResponse.options_response(dict(HTTP_REFERER='http://example.com'))
    assert ('Access-Control-Allow-Origin', 'http://example.com') in res.status_headers.headers
    res = WbResponse.options_response(dict())
    assert ('Access-Control-Allow-Origin', '*') in res.status_headers.headers
    res = WbResponse.options_response(dict(HTTP_ORIGIN=None))
    assert ('Access-Control-Allow-Origin', '*') in res.status_headers.headers
    res = WbResponse.options_response(dict(HTTP_REFERER=None))
    assert ('Access-Control-Allow-Origin', '*') in res.status_headers.headers


def test_wbresponse_json_response():
    body = dict(pywb=1, wr=2)
    res = WbResponse.json_response(body)
    status_headers = res.status_headers
    assert status_headers.statusline == '200 OK'
    assert ('Content-Type', 'application/json; charset=utf-8') in status_headers.headers
    assert json.loads(res.body[0]) == body


def test_wbresponse_init_derived():
    class Derived(WbResponse):
        def __init__(self, status_headers, value=None, **kwargs):
            self.received_kwargs = dict()
            super(Derived, self).__init__(status_headers, value=value, **kwargs)

        def _init_derived(self, params):
            self.received_kwargs.update(params)

    dres = Derived(None,  pywb=1, wr=2)
    assert dres.received_kwargs == dict(pywb=1, wr=2)


def test_wbresponse_callable():
    expected_body = dict(pywb=1, wr=2)
    res = WbResponse.json_response(expected_body)
    env = dict(REQUEST_METHOD='GET')
    expected_passed_values = dict(
        status_line='200 OK',
        headers=[('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', '17')]
    )
    passed_values = dict(status_line=None, headers=None)

    def start_response(status_line, headers):
        passed_values['status_line'] = status_line
        passed_values['headers'] = headers

    body = res(env, start_response)
    assert json.loads(body[0]) == expected_body
    assert passed_values == expected_passed_values


if __name__ == "__main__":
    import doctest
    doctest.testmod()

