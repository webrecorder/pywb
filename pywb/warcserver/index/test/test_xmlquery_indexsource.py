from pywb.warcserver.test.testutils import BaseTestClass, key_ts_res

from pywb.warcserver.index.indexsource import XmlQueryIndexSource
from pywb.warcserver.index.aggregator import SimpleAggregator

from six.moves.urllib.parse import quote_plus

from mock import patch
import pytest


query_url = None


# ============================================================================
def mock_get(self, url):
    string = ''
    global query_url
    query_url = url
    if quote_plus(XmlQueryIndexSource.EXACT_QUERY) in url:
        if quote_plus(quote_plus('http://example.com/some/path')) in url:
            string = URL_RESPONSE_2

        elif quote_plus(quote_plus('http://example.com/')) in url:
            string = URL_RESPONSE_1

    elif quote_plus(XmlQueryIndexSource.PREFIX_QUERY) in url:
        string = PREFIX_QUERY

    class MockResponse(object):
        def __init__(self, string):
            self.string = string

        @property
        def text(self):
            return self.string

        @property
        def content(self):
            return self.string.encode('utf-8')

        def raise_for_status(self):
            pass


    return MockResponse(string)


# ============================================================================
class TestXmlQueryIndexSource(BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestXmlQueryIndexSource, cls).setup_class()

        cls.xmlpatch = patch('pywb.warcserver.index.indexsource.etree', cls._get_etree())
        cls.xmlpatch.start()

    @classmethod
    def _get_etree(cls):
        import xml.etree.ElementTree as etree
        return etree

    @classmethod
    def teardown_class(cls):
        cls.xmlpatch.stop()
        super(TestXmlQueryIndexSource, cls).teardown_class()

    def do_query(self, params):
        return SimpleAggregator({'source': XmlQueryIndexSource('http://localhost:8080/path')})(params)

    @patch('pywb.warcserver.index.indexsource.requests.sessions.Session.get', mock_get)
    def test_exact_query(self):
        res, errs = self.do_query({'url': 'http://example.com/', 'limit': 100})
        reslist = list(res)

        expected = """\
com,example)/ 20180112200243 example.warc.gz
com,example)/ 20180216200300 example.warc.gz"""
        assert(key_ts_res(reslist) == expected)
        assert(errs == {})
        assert query_url == 'http://localhost:8080/path?q=limit%3A100+type%3Aurlquery+url%3Ahttp%253A%252F%252Fexample.com%252F'
        assert reslist[0]['length'] == '123'
        assert 'length' not in reslist[1]


    @patch('pywb.warcserver.index.indexsource.requests.sessions.Session.get', mock_get)
    def test_exact_query_2(self):
        res, errs = self.do_query({'url': 'http://example.com/some/path'})
        expected = """\
com,example)/some/path 20180112200243 example.warc.gz
com,example)/some/path 20180216200300 example.warc.gz"""
        assert(key_ts_res(res) == expected)
        assert(errs == {})

        assert query_url == 'http://localhost:8080/path?q=type%3Aurlquery+url%3Ahttp%253A%252F%252Fexample.com%252Fsome%252Fpath'


    @patch('pywb.warcserver.index.indexsource.requests.sessions.Session.get', mock_get)
    def test_prefix_query(self):
        res, errs = self.do_query({'url': 'http://example.com/', 'matchType': 'prefix'})
        expected = """\
com,example)/ 20180112200243 example.warc.gz
com,example)/ 20180216200300 example.warc.gz
com,example)/some/path 20180112200243 example.warc.gz
com,example)/some/path 20180216200300 example.warc.gz"""
        assert(key_ts_res(res) == expected)
        assert(errs == {})


# ============================================================================
class TestXmlQueryIndexSourceLXML(TestXmlQueryIndexSource):
    @classmethod
    def _get_etree(cls):
        pytest.importorskip('lxml.etree')
        import lxml.etree
        return lxml.etree


# ============================================================================
URL_RESPONSE_1 = """
<wayback>
   <results>
       <result>
         <compressedoffset>10</compressedoffset>
         <compressedendoffset>123</compressedendoffset>
         <mimetype>text/html</mimetype>
         <file>example.warc.gz</file>
         <redirecturl>-</redirecturl>
         <urlkey>com,example)/</urlkey>
         <digest>7NZ7K6ZTRC4SOJODXH3S4AGZV7QSBWLF</digest>
         <httpresponsecode>200</httpresponsecode>
         <robotflags>-</robotflags>
         <url>http://example.ccom/</url>
         <capturedate>20180112200243</capturedate>
      </result>
      <result>
         <compressedoffset>29570</compressedoffset>
         <mimetype>text/html</mimetype>
         <file>example.warc.gz</file>
         <redirecturl>-</redirecturl>
         <urlkey>com,example)/</urlkey>
         <digest>LCKPKJJU5VPEN6HUJZ6JUYRGTPFD7ZC3</digest>
         <httpresponsecode>200</httpresponsecode>
         <robotflags>-</robotflags>
         <url>http://example.com/</url>
         <capturedate>20180216200300</capturedate>
      </result>
   </results>
</wayback>
"""

URL_RESPONSE_2 = """
<wayback>
   <results>
       <result>
         <compressedoffset>10</compressedoffset>
         <mimetype>text/html</mimetype>
         <file>example.warc.gz</file>
         <redirecturl>-</redirecturl>
         <urlkey>com,example)/some/path</urlkey>
         <digest>7NZ7K6ZTRC4SOJODXH3S4AGZV7QSBWLF</digest>
         <httpresponsecode>200</httpresponsecode>
         <robotflags>-</robotflags>
         <url>http://example.com/some/path</url>
         <capturedate>20180112200243</capturedate>
      </result>
      <result>
         <compressedoffset>29570</compressedoffset>
         <mimetype>text/html</mimetype>
         <file>example.warc.gz</file>
         <redirecturl>-</redirecturl>
         <urlkey>com,example)/some/path</urlkey>
         <digest>LCKPKJJU5VPEN6HUJZ6JUYRGTPFD7ZC3</digest>
         <httpresponsecode>200</httpresponsecode>
         <robotflags>-</robotflags>
         <url>http://example.com/some/path</url>
         <capturedate>20180216200300</capturedate>
      </result>
  </results>
</wayback>
"""

PREFIX_QUERY = """
<wayback>
    <results>
        <result>
            <urlkey>com,example)/</urlkey>
            <originalurl>http://example.com/</originalurl>
            <numversions>2</numversions>
            <numcaptures>2</numcaptures>
            <firstcapturets>20180112200243</firstcapturets>
            <lastcapturets>20180216200300</lastcapturets>
        </result>
        <result>
            <urlkey>com,example)/some/path</urlkey>
            <originalurl>http://example.com/some/path</originalurl>
            <numversions>2</numversions>
            <numcaptures>2</numcaptures>
            <firstcapturets>20180112200243</firstcapturets>
            <lastcapturets>20180216200300</lastcapturets>
        </result>
    </results>
</wayback>
"""
