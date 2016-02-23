import re
import webtest

from six.moves.urllib.parse import urlencode

from pywb.cdx.cdxobject import CDXObject
from pywb.apps.cdx_server import application

import pytest
import json


#================================================================
@pytest.fixture
def client():
    return webtest.TestApp(application)


#================================================================
def query(client, url, is_error=False, **params):
    params['url'] = url
    return client.get('/pywb-cdx?' + urlencode(params, doseq=1), expect_errors=is_error)


#================================================================
def test_exact_url(client):
    """
    basic exact match, no filters, etc.
    """
    resp = query(client, 'http://www.iana.org/')

    assert resp.status_code == 200
    assert len(resp.text.splitlines()) == 3, resp.text


#================================================================
def test_exact_url_json(client):
    """
    basic exact match, no filters, etc.
    """
    resp = query(client, 'http://www.iana.org/', output='json')

    assert resp.status_code == 200
    lines = resp.text.splitlines()
    assert len(lines) == 3, resp.text
    assert len(list(map(json.loads, lines))) == 3

#================================================================
def test_prefix_match(client):
    """
    prefix match test
    """
    resp = query(client, 'http://www.iana.org/', matchType='prefix')

    print(resp.text.splitlines())
    assert resp.status_code == 200

    suburls = 0
    for l in resp.text.splitlines():
        fields = l.split(' ')
        if len(fields[0]) > len('org,iana)/'):
            suburls += 1
    assert suburls > 0


#================================================================
def test_filters(client):
    """
    filter cdxes by mimetype and filename field, exact match.
    """
    resp = query(client, 'http://www.iana.org/_css/2013.1/screen.css',
                 filter=('mime:warc/revisit', 'filename:dupes.warc.gz'))

    assert resp.status_code == 200
    assert resp.content_type == 'text/plain'

    for l in resp.text.splitlines():
        fields = l.split(' ')
        assert fields[0] == 'org,iana)/_css/2013.1/screen.css'
        assert fields[3] == 'warc/revisit'
        assert fields[10] == 'dupes.warc.gz'


#================================================================
def test_limit(client):
    resp = query(client, 'http://www.iana.org/_css/2013.1/screen.css',
                 limit='1')

    assert resp.status_code == 200
    assert resp.content_type == 'text/plain'

    cdxes = resp.text.splitlines()
    assert len(cdxes) == 1
    fields = cdxes[0].split(' ')
    assert fields[0] == 'org,iana)/_css/2013.1/screen.css'
    assert fields[1] == '20140126200625'
    assert fields[3] == 'text/css'

    resp = query(client, 'http://www.iana.org/_css/2013.1/screen.css',
                 limit='1', reverse='1')

    assert resp.status_code == 200
    assert resp.content_type == 'text/plain'

    cdxes = resp.text.splitlines()
    assert len(cdxes) == 1
    fields = cdxes[0].split(' ')
    assert fields[0] == 'org,iana)/_css/2013.1/screen.css'
    assert fields[1] == '20140127171239'
    assert fields[3] == 'warc/revisit'


#================================================================
def test_fields(client):
    """
    retrieve subset of fields with ``fields`` parameter.
    """
    resp = query(client, 'http://www.iana.org/_css/2013.1/print.css',
                 fields='urlkey,timestamp,status')

    assert resp.status_code == 200

    cdxes = resp.text.splitlines()

    for cdx in cdxes:
        fields = cdx.split(' ')
        assert len(fields) == 3
        assert fields[0] == 'org,iana)/_css/2013.1/print.css'
        assert re.match(r'\d{14}$', fields[1])
        assert re.match(r'\d{3}|-', fields[2])


#================================================================
def test_fields_json(client):
    """
    retrieve subset of fields with ``fields`` parameter, in json
    """
    resp = query(client, 'http://www.iana.org/_css/2013.1/print.css',
                 fields='urlkey,timestamp,status',
                 output='json')

    assert resp.status_code == 200

    cdxes = resp.text.splitlines()

    for cdx in cdxes:
        fields = json.loads(cdx)
        assert len(fields) == 3
        assert fields['urlkey'] == 'org,iana)/_css/2013.1/print.css'
        assert re.match(r'\d{14}$', fields['timestamp'])
        assert re.match(r'\d{3}|-', fields['status'])


#================================================================
def test_fields_undefined(client):
    """
    server shall respond with Bad Request and name of undefined
    when ``fields`` parameter contains undefined name(s).
    """
    resp = query(client, 'http://www.iana.org/_css/2013.1/print.css',
                 is_error=True,
                 fields='urlkey,nosuchfield')

    resp.status_code == 400


#================================================================
def test_fields_undefined_json(client):
    """
    server shall respond with Bad Request and name of undefined
    when ``fields`` parameter contains undefined name(s).
    """
    resp = query(client, 'http://www.iana.org/_css/2013.1/print.css',
                 is_error=True,
                 fields='urlkey,nosuchfield',
                 output='json')

    resp.status_code == 400

#================================================================
def test_resolveRevisits(client):
    """
    with ``resolveRevisits=true``, server adds three fields pointing to
    the *original* capture.
    """
    resp = query(client, 'http://www.iana.org/_css/2013.1/print.css',
                 resolveRevisits='true'
                 )
    assert resp.status_code == 200
    assert resp.content_type == 'text/plain'

    cdxes = resp.text.splitlines()
    originals = {}
    for cdx in cdxes:
        fields = cdx.split(' ')
        assert len(fields) == 14
        (key, ts, url, mt, st, sha, _, _, size, offset, fn,
         orig_size, orig_offset, orig_fn) = fields
        # orig_* fields are either all '-' or (int, int, filename)
        # check if orig_* fields are equals to corresponding fields
        # for the original capture.
        if orig_size == '-':
            assert orig_offset == '-' and orig_fn == '-'
            originals[sha] = (int(size), int(offset), fn)
        else:
            orig = originals.get(sha)
            assert orig == (int(orig_size), int(orig_offset), orig_fn)


#================================================================
def test_resolveRevisits_orig_fields(client):
    """
    when resolveRevisits=true, extra three fields are named
    ``orig.length``, ``orig.offset`` and ``orig.filename``, respectively.
    it is possible to filter fields by these names.
    """
    resp = query(client, 'http://www.iana.org/_css/2013.1/print.css',
                 resolveRevisits='1',
                 fields='urlkey,orig.length,orig.offset,orig.filename'
                 )
    assert resp.status_code == 200
    assert resp.content_type == 'text/plain'

    cdxes = resp.text.splitlines()
    for cdx in cdxes:
        fields = cdx.split(' ')
        assert len(fields) == 4
        key, orig_len, orig_offset, orig_fn = fields
        assert (orig_len == '-' and orig_offset == '-' and orig_fn == '-' or
                (int(orig_len), int(orig_offset), orig_fn))


#================================================================
def test_collapseTime_resolveRevisits_reverse(client):
    resp = query(client, 'http://www.iana.org/_css/2013.1/print.css',
                 collapseTime='11',
                 resolveRevisits='true',
                 reverse='true'
                 )

    cdxes = [CDXObject(l) for l in resp.body.splitlines()]

    assert len(cdxes) == 3

    # timestamp is in descending order
    for i in range(len(cdxes) - 1):
        assert cdxes[i]['timestamp'] >= cdxes[i + 1]['timestamp']
