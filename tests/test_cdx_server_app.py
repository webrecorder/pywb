from gevent import monkey; monkey.patch_all(thread=False)

import re
import json
import os

import webtest

from six.moves.urllib.parse import urlencode

from pywb.warcserver.index.cdxobject import CDXObject

from pywb.warcserver.test.testutils import BaseTestClass
from pywb.warcserver.warcserver import WarcServer


# ============================================================================
class TestCDXApp(BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestCDXApp, cls).setup_class()
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config_test.yaml')
        cls.testapp = webtest.TestApp(WarcServer(config_file=config_file))

    def query(self, url, is_error=False, **params):
        params['url'] = url
        return self.testapp.get('/pywb/index?' + urlencode(params, doseq=1), expect_errors=is_error)

    def test_exact_url(self):
        """
        basic exact match, no filters, etc.
        """
        resp = self.query('http://www.iana.org/')

        assert resp.status_code == 200
        assert len(resp.text.splitlines()) == 3, resp.text

    def test_exact_url_json(self):
        """
        basic exact match, no filters, etc.
        """
        resp = self.query('http://www.iana.org/', output='json')

        assert resp.status_code == 200
        lines = resp.text.splitlines()
        assert len(lines) == 3, resp.text
        assert len(list(map(json.loads, lines))) == 3

    def test_exact_url_plain_text(self):
        """
        basic exact match, no filters, etc.
        """
        resp = self.query('http://www.iana.org/', output='text')

        assert resp.status_code == 200
        assert resp.content_type == 'text/plain'
        assert '{' not in resp.text

        lines = resp.text.splitlines()
        assert len(lines) == 3, resp.text

    def test_prefix_match(self):
        """
        prefix match test
        """
        resp = self.query('http://www.iana.org/', matchType='prefix')

        assert resp.status_code == 200

        suburls = 0
        for l in resp.text.splitlines():
            fields = l.split(' ')
            if len(fields[0]) > len('org,iana)/'):
                suburls += 1
        assert suburls > 0

    def test_filters_1(self):
        """
        filter cdxes by mimetype and filename field, exact match.
        """
        resp = self.query('http://www.iana.org/_css/2013.1/screen.css',
                     filter=('mime:warc/revisit', 'filename:dupes.warc.gz'))

        assert resp.status_code == 200
        assert resp.content_type == 'text/x-cdxj'

        lines = resp.text.splitlines()
        assert len(lines) > 0

        for l in lines:
            cdx = CDXObject(l.encode('utf-8'))
            assert cdx['urlkey'] == 'org,iana)/_css/2013.1/screen.css'
            assert cdx['timestamp'] == '20140127171239'
            assert cdx['mime'] == 'warc/revisit'
            assert cdx['filename'] == 'dupes.warc.gz'

    def test_filters_2_no_fuzzy_no_match(self):
        """
        two filters, disable fuzzy matching
        """
        resp = self.query('http://www.iana.org/_css/2013.1/screen.css',
                     filter=('!mime:warc/revisit', 'filename:dupes.warc.gz'),
                     allowFuzzy='false')

        assert resp.status_code == 200
        assert resp.content_type == 'text/x-cdxj'

        lines = resp.text.splitlines()
        assert len(lines) == 0

    def test_filters_3(self):
        """
        filter cdxes by mimetype and filename field, exact match.
        """
        resp = self.query('http://www.iana.org/_css/2013.1/screen.css',
                     filter=('!mime:warc/revisit', '!filename:dupes.warc.gz'))

        assert resp.status_code == 200
        assert resp.content_type == 'text/x-cdxj'

        lines = resp.text.splitlines()
        assert len(lines) == 1

        for l in lines:
            cdx = CDXObject(l.encode('utf-8'))
            assert cdx['urlkey'] == 'org,iana)/_css/2013.1/screen.css'
            assert cdx['timestamp'] == '20140126200625'
            assert cdx['mime'] == 'text/css'
            assert cdx['filename'] == 'iana.warc.gz'

    def test_limit(self):
        resp = self.query('http://www.iana.org/_css/2013.1/screen.css',
                     limit='1')

        assert resp.status_code == 200
        assert resp.content_type == 'text/x-cdxj'

        cdxes = resp.text.splitlines()
        assert len(cdxes) == 1

        cdx = CDXObject(cdxes[0].encode('utf-8'))
        assert cdx['urlkey'] == 'org,iana)/_css/2013.1/screen.css'
        assert cdx['timestamp'] == '20140126200625'
        assert cdx['mime'] == 'text/css'

        resp = self.query('http://www.iana.org/_css/2013.1/screen.css',
                     limit='1', reverse='1')

        assert resp.status_code == 200
        assert resp.content_type == 'text/x-cdxj'

        cdxes = resp.text.splitlines()
        assert len(cdxes) == 1

        cdx = CDXObject(cdxes[0].encode('utf-8'))
        assert cdx['urlkey'] == 'org,iana)/_css/2013.1/screen.css'
        assert cdx['timestamp'] == '20140127171239'
        assert cdx['mime'] == 'warc/revisit'

    def test_fields(self):
        """
        retrieve subset of fields with ``fields`` parameter.
        """
        resp = self.query('http://www.iana.org/_css/2013.1/print.css',
                     fields='urlkey,timestamp,status')

        assert resp.status_code == 200

        cdxes = resp.text.splitlines()

        for cdx in cdxes:
            cdx = CDXObject(cdx.encode('utf-8'))
            assert cdx['urlkey'] == 'org,iana)/_css/2013.1/print.css'
            assert re.match(r'\d{14}$', cdx['timestamp'])
            assert re.match(r'\d{3}|-', cdx['status'])

    def test_fields_json(self):
        """
        retrieve subset of fields with ``fields`` parameter, in json
        """
        resp = self.query('http://www.iana.org/_css/2013.1/print.css',
                     fields='urlkey,timestamp,status',
                     output='json')

        assert resp.status_code == 200

        cdxes = resp.text.splitlines()

        for cdx in cdxes:
            print(cdx)
            fields = json.loads(cdx)
            assert len(fields) == 3
            assert fields['urlkey'] == 'org,iana)/_css/2013.1/print.css'
            assert re.match(r'\d{14}$', fields['timestamp'])
            assert re.match(r'\d{3}|-', fields['status'])

    def test_fields_undefined(self):
        """
        server shall respond with Bad Request and name of undefined
        when ``fields`` parameter contains undefined name(s).
        """
        resp = self.query('http://www.iana.org/_css/2013.1/print.css',
                     is_error=True,
                     fields='urlkey,nosuchfield')

        resp.status_code == 400

    def test_fields_undefined_json(self):
        """
        server shall respond with Bad Request and name of undefined
        when ``fields`` parameter contains undefined name(s).
        """
        resp = self.query('http://www.iana.org/_css/2013.1/print.css',
                     is_error=True,
                     fields='urlkey,nosuchfield',
                     output='json')

        resp.status_code == 400

    def test_resolveRevisits(self):
        """
        with ``resolveRevisits=true``, server adds three fields pointing to
        the *original* capture.
        """
        resp = self.query('http://www.iana.org/_css/2013.1/print.css',
                     resolveRevisits='true'
                     )
        assert resp.status_code == 200
        assert resp.content_type == 'text/x-cdxj'

        cdxes = resp.text.splitlines()
        originals = {}
        for cdx in cdxes:
            cdx = CDXObject(cdx.encode('utf-8'))
            assert len(cdx) == 16

            # orig.* fields are either all '-' or (int, int, filename)
            # check if orig.* fields are equals to corresponding fields
            # for the original capture.

            sha = cdx['digest']
            if cdx['orig.length'] == '-':
                assert cdx['orig.offset'] == '-' and cdx['orig.filename'] == '-'
                originals[sha] = (int(cdx['length']), int(cdx['offset']), cdx['filename'])
            else:
                orig = originals.get(sha)
                assert orig == (int(cdx['orig.length']), int(cdx['orig.offset']), cdx['orig.filename'])

    def test_resolveRevisits_orig_fields(self):
        """
        when resolveRevisits=true, extra three fields are named
        ``orig.length``, ``orig.offset`` and ``orig.filename``, respectively.
        it is possible to filter fields by these names.
        """
        resp = self.query('http://www.iana.org/_css/2013.1/print.css',
                     resolveRevisits='1',
                     fields='urlkey,orig.length,orig.offset,orig.filename'
                     )
        assert resp.status_code == 200
        assert resp.content_type == 'text/x-cdxj'

        cdxes = resp.text.splitlines()
        cdx = cdxes[0]
        cdx = CDXObject(cdx.encode('utf-8'))
        assert cdx['orig.offset'] == '-'
        assert cdx['orig.length'] == '-'
        assert cdx['orig.filename'] == '-'

        for cdx in cdxes[1:]:
            cdx = CDXObject(cdx.encode('utf-8'))
            assert cdx['orig.offset'] != '-'
            assert cdx['orig.length'] != '-'
            assert cdx['orig.filename'] == 'iana.warc.gz'

    def test_collapseTime_resolveRevisits_reverse(self):
        resp = self.query('http://www.iana.org/_css/2013.1/print.css',
                     collapseTime='11',
                     resolveRevisits='true',
                     reverse='true'
                     )

        cdxes = [CDXObject(l) for l in resp.body.splitlines()]

        assert len(cdxes) == 3

        # timestamp is in descending order
        for i in range(len(cdxes) - 1):
            assert cdxes[i]['timestamp'] >= cdxes[i + 1]['timestamp']

    def test_error_unknown_output_format(self):
        """test unknown output format in combination with a list of output fields"""
        resp = self.query('http://www.iana.org/_css/2013.1/print.css',
                          is_error=True,
                          fields='urlkey,timestamp,status',
                          output='foo')
        assert resp.status_code == 400
        assert resp.json == {'message': 'output=foo not supported'}

    def test_error_unknown_match_type(self):
        """test unknown/unsupported matchType"""
        resp = self.query('http://www.iana.org/_css/2013.1/print.css',
                          is_error=True,
                          fields='urlkey,timestamp,status',
                          matchType='foo')
        assert resp.status_code == 400
        assert resp.json == {'message': 'Invalid match_type: foo'}

