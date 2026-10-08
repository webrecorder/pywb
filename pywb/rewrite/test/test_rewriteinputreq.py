from pywb.rewrite.rewriteinputreq import RewriteInputRequest

import pytest


# ============================================================================
URL = 'https://example.com/path'


def get_req_headers(env, url=URL):
    env.setdefault('REQUEST_METHOD', 'GET')
    return RewriteInputRequest(env, 'com,example)/path', url, None).get_req_headers()


@pytest.mark.parametrize('dest', ['iframe', 'frame', 'IFrame'])
def test_sec_fetch_dest_frame_sent_as_document(dest):
    headers = get_req_headers({'HTTP_SEC_FETCH_DEST': dest})
    assert headers['Sec-Fetch-Dest'] == 'document'


@pytest.mark.parametrize('dest', ['document', 'image', 'script', 'empty'])
def test_sec_fetch_dest_other_unchanged(dest):
    headers = get_req_headers({'HTTP_SEC_FETCH_DEST': dest})
    assert headers['Sec-Fetch-Dest'] == dest


def test_sec_fetch_dest_missing_not_added():
    headers = get_req_headers({'HTTP_ACCEPT': 'text/html'})
    assert 'Sec-Fetch-Dest' not in headers


def test_sec_fetch_dest_proxy_unchanged():
    headers = get_req_headers({'HTTP_SEC_FETCH_DEST': 'iframe',
                               'wsgiprox.proxy_host': 'pywb.proxy'})
    assert headers['Sec-Fetch-Dest'] == 'iframe'


def test_sec_fetch_dest_other_sec_fetch_unchanged():
    headers = get_req_headers({'HTTP_SEC_FETCH_DEST': 'iframe',
                               'HTTP_SEC_FETCH_MODE': 'navigate',
                               'HTTP_SEC_FETCH_SITE': 'same-origin'})
    assert headers['Sec-Fetch-Dest'] == 'document'
    assert headers['Sec-Fetch-Mode'] == 'navigate'
    assert headers['Sec-Fetch-Site'] == 'same-origin'
