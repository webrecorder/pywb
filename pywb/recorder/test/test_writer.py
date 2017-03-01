from pywb.utils.statusandheaders import StatusAndHeaders
from pywb.recorder.warcwriter import SimpleTempWARCWriter
from pywb.warc.recordloader import ArcWarcRecordLoader
from pywb.warc.archiveiterator import ArchiveIterator

from io import BytesIO
from collections import OrderedDict
import json


# ============================================================================
class FixedTestWARCWriter(SimpleTempWARCWriter):
    @classmethod
    def _make_warc_id(cls, id_=None):
        return '<urn:uuid:12345678-feb0-11e6-8f83-68a86d1772ce>'

    @classmethod
    def _make_warc_date(cls):
        return '2000-01-01T00:00:00Z'


# ============================================================================
class TestWarcWriter(object):
    def _validate_record_content_len(self, stream):
        for record in ArchiveIterator(stream, no_record_parse=True):
            assert record.status_headers == None
            assert int(record.rec_headers.get_header('Content-Length')) == record.length
            assert record.length == len(record.stream.read())


    def test_warcinfo_record(self):
        simplewriter = FixedTestWARCWriter(gzip=False)
        params = OrderedDict([('software', 'recorder test'),
                              ('format', 'WARC File Format 1.0'),
                              ('json-metadata', json.dumps({'foo': 'bar'}))])

        record = simplewriter.create_warcinfo_record('testfile.warc.gz', params)
        simplewriter.write_record(record)
        buff = simplewriter.get_buffer()
        assert isinstance(buff, bytes)

        buff = BytesIO(buff)
        parsed_record = ArcWarcRecordLoader().parse_record_stream(buff)

        assert parsed_record.rec_headers.get_header('WARC-Type') == 'warcinfo'
        assert parsed_record.rec_headers.get_header('Content-Type') == 'application/warc-fields'
        assert parsed_record.rec_headers.get_header('WARC-Filename') == 'testfile.warc.gz'

        buff = parsed_record.stream.read().decode('utf-8')

        length = parsed_record.rec_headers.get_header('Content-Length')

        assert len(buff) == int(length)

        assert 'json-metadata: {"foo": "bar"}\r\n' in buff
        assert 'format: WARC File Format 1.0\r\n' in buff

        warcinfo_record = '\
WARC/1.0\r\n\
WARC-Type: warcinfo\r\n\
WARC-Record-ID: <urn:uuid:12345678-feb0-11e6-8f83-68a86d1772ce>\r\n\
WARC-Filename: testfile.warc.gz\r\n\
WARC-Date: 2000-01-01T00:00:00Z\r\n\
Content-Type: application/warc-fields\r\n\
Content-Length: 86\r\n\
\r\n\
software: recorder test\r\n\
format: WARC File Format 1.0\r\n\
json-metadata: {"foo": "bar"}\r\n\
\r\n\
\r\n\
'

        assert simplewriter.get_buffer().decode('utf-8') == warcinfo_record

    def test_generate_response(self):
        headers_list = [('Content-Type', 'text/plain; charset="UTF-8"'),
                        ('Custom-Header', 'somevalue')
                       ]

        payload = b'some\ntext'

        status_headers = StatusAndHeaders('200 OK', headers_list, protocol='HTTP/1.0')


        writer = FixedTestWARCWriter(gzip=False)

        record = writer.create_warc_record('http://example.com/', 'response',
                                           payload=BytesIO(payload),
                                           length=len(payload),
                                           status_headers=status_headers)


        writer.write_record(record)

        buff = writer.get_buffer()

        self._validate_record_content_len(BytesIO(buff))

        warc_record = '\
WARC/1.0\r\n\
WARC-Type: response\r\n\
WARC-Record-ID: <urn:uuid:12345678-feb0-11e6-8f83-68a86d1772ce>\r\n\
WARC-Target-URI: http://example.com/\r\n\
WARC-Date: 2000-01-01T00:00:00Z\r\n\
WARC-Block-Digest: sha1:B6QJ6BNJ3R4B23XXMRKZKHLPGJY2VE4O\r\n\
WARC-Payload-Digest: sha1:B6QJ6BNJ3R4B23XXMRKZKHLPGJY2VE4O\r\n\
Content-Type: application/http; msgtype=response\r\n\
Content-Length: 97\r\n\
\r\n\
HTTP/1.0 200 OK\r\n\
Content-Type: text/plain; charset="UTF-8"\r\n\
Custom-Header: somevalue\r\n\
\r\n\
some\n\
text\
\r\n\
\r\n\
'
        assert buff.decode('utf-8') == warc_record

