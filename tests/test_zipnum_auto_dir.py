from .base_config_test import BaseConfigTest, CollsDirMixin
from pywb.manager.manager import main as manager

from pywb.warcserver.index.cdxobject import CDXObject
import shutil
from pywb import get_test_dir
import os
import json


# ============================================================================
class TestZipnumAutoDir(CollsDirMixin, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestZipnumAutoDir, cls).setup_class('config_test.yaml')

        manager(['init', 'testzip'])

        cls.archive_dir = os.path.join(cls.root_dir, '_test_colls', 'testzip', 'archive')
        cls.index_dir = os.path.join(cls.root_dir, '_test_colls', 'testzip', 'indexes')

        zip_cdx = os.path.join(get_test_dir(), 'zipcdx')

        shutil.copy(os.path.join(zip_cdx, 'zipnum-sample.idx'), cls.index_dir)
        shutil.copy(os.path.join(zip_cdx, 'zipnum-sample.cdx.gz'), cls.index_dir)
        shutil.copy(os.path.join(zip_cdx, 'zipnum-sample.loc'), cls.index_dir)

        shutil.copy(os.path.join(get_test_dir(), 'warcs', 'iana.warc.gz'), cls.archive_dir)

    def test_cdxj_query(self):
        res = self.testapp.get('/testzip/cdx?url=iana.org/domains/*')
        assert len(res.text.rstrip().split('\n')) == 9

    def test_num_pages_query(self):
        res = self.testapp.get('/testzip/cdx?url=http://iana.org/domains/&matchType=domain&showNumPages=true&pageSize=4')
        res.content_type = 'text/json'
        assert(res.json == {"blocks": 38, "pages": 10, "pageSize": 4})

    def test_paged_index_query(self):
        res = self.testapp.get('/testzip/cdx?url=http://iana.org/domains/&matchType=domain&output=json&showPagedIndex=true&pageSize=4&page=1')

        lines = [json.loads(line) for line in res.text.rstrip().split('\n')]

        assert lines[0] == {"urlkey": "org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200912", "part": "zipnum", "offset": 1150, "length": 235, "lineno": 5}
        assert lines[1] == {"urlkey": "org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126201240", "part": "zipnum", "offset": 1385, "length": 307, "lineno": 6}
        assert lines[2] == {"urlkey": "org,iana)/_css/2013.1/fonts/opensans-regular.ttf 20140126200654", "part": "zipnum", "offset": 1692, "length": 235, "lineno": 7}
        assert lines[3] == {"urlkey": "org,iana)/_css/2013.1/fonts/opensans-regular.ttf 20140126200816", "part": "zipnum", "offset": 1927, "length": 231, "lineno": 8}

    def test_paged_index_query_out_of_range(self):
        res = self.testapp.get(
            '/testzip/cdx?url=http://iana.org/domains/&matchType=domain&output=json&showPagedIndex=true&pageSize=4&page=10',
            expect_errors=True)

        assert res.status_code == 400
        assert res.json == {"message": "Page 10 invalid: First Page is 0, Last Page is 9"}



