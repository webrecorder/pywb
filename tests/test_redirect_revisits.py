from .base_config_test import BaseConfigTest, CollsDirMixin, fmod

from io import BytesIO
import os

from warcio import WARCWriter, StatusAndHeaders
from pywb.manager.manager import main as wb_manager


# ============================================================================
class TestRevisits(CollsDirMixin, BaseConfigTest):
    @classmethod
    def setup_class(cls):
        super(TestRevisits, cls).setup_class('config_test.yaml')


    def create_revisit_record(self, url, date, headers, refers_to_uri, refers_to_date):
        http_headers = StatusAndHeaders(
            "301 Permanent Redirect", headers, protocol="HTTP/1.0"
        )

        return self.writer.create_revisit_record(
            url,
            digest="sha1:B6QJ6BNJ3R4B23XXMRKZKHLPGJY2VE4O",
            refers_to_uri=refers_to_uri,
            refers_to_date=refers_to_date,
            warc_headers_dict={"WARC-Date": date},
            http_headers=http_headers,
        )


    def create_response_record(self, url, date, headers, payload):
        http_headers = StatusAndHeaders(
            "301 Permanent Redirect", headers, protocol="HTTP/1.0"
        )

        return self.writer.create_warc_record(
            url,
            record_type="response",
            http_headers=http_headers,
            payload=BytesIO(payload),
            warc_headers_dict={"WARC-Date": date},
            length=len(payload),
        )

    def create(self):
        payload = b"some\ntext"

        # record 1
        self.writer.write_record(
            self.create_response_record(
                "http://example.com/orig-1",
                "2020-01-01T00:00:00Z",
                [
                    ("Content-Type", 'text/plain; charset="UTF-8"'),
                    ("Location", "https://example.com/redirect-1"),
                    ("Content-Length", str(len(payload))),
                    ("Custom", "1"),
                ],
                payload,
            )
        )

        # record 2
        self.writer.write_record(
            self.create_response_record(
                "http://example.com/orig-2",
                "2020-01-01T00:00:00Z",
                [
                    ("Content-Type", 'text/plain; charset="UTF-8"'),
                    ("Location", "https://example.com/redirect-2"),
                    ("Content-Length", str(len(payload))),
                    ("Custom", "2"),
                ],
                payload,
            )
        )

        # record 3
        self.writer.write_record(
            self.create_revisit_record(
                "http://example.com/orig-2",
                "2022-01-01T00:00:00Z",
                [
                    ("Content-Type", 'text/plain; charset="UTF-8"'),
                    ("Location", "https://example.com/redirect-3"),
                    ("Content-Length", str(len(payload))),
                    ("Custom", "3"),
                ],
                refers_to_uri="http://example.com/orig-1",
                refers_to_date="2020-01-01T00:00:00Z",
            )
        )

        # record 4
        self.writer.write_record(
            self.create_revisit_record(
                "http://example.com/",
                "2022-01-01T00:00:00Z",
                [
                    ("Content-Type", 'text/plain; charset="UTF-8"'),
                    ("Location", "https://example.com/redirect-4"),
                    ("Content-Length", str(len(payload))),
                    ("Custom", "4"),
                ],
                refers_to_uri="http://example.com/orig-2",
                refers_to_date="2020-01-01T00:00:00Z",
            )
        )

    def test_init(self):
        filename = os.path.join(self.root_dir, 'redir.warc.gz')
        with open(filename, 'wb') as fh:
            self.writer = WARCWriter(fh, gzip=True)
            self.create()

        wb_manager(['init', 'revisits'])

        wb_manager(['add', 'revisits', filename])

        assert os.path.isfile(os.path.join(self.root_dir, self.COLLS_DIR, 'revisits', 'indexes', 'index.cdxj'))

    def test_different_url_revisit_orig_headers(self, fmod):
        res = self.get('/revisits/20220101{0}/http://example.com/', fmod, status=301)
        assert res.headers["Custom"] == "4"
        assert res.headers["Location"].endswith("/20220101{0}/https://example.com/redirect-4".format(fmod))
        assert res.content_length == 0
        assert res.text == ''

    def test_different_url_response_and_revisit(self, fmod):
        # response
        res = self.get('/revisits/20200101{0}/http://example.com/orig-2', fmod, status=301)
        assert res.headers["Custom"] == "2"
        assert res.headers["Location"].endswith("/20200101{0}/https://example.com/redirect-2".format(fmod))
        assert res.text == 'some\ntext'

        # revisit
        res = self.get('/revisits/20220101{0}/http://example.com/orig-2', fmod, status=301)
        assert res.headers["Custom"] == "3"
        assert res.headers["Location"].endswith("/20220101{0}/https://example.com/redirect-3".format(fmod))
        assert res.content_length == 0
        assert res.text == ''

    def test_orig(self, fmod):
        res = self.get('/revisits/20200101{0}/http://example.com/orig-1', fmod, status=301)
        assert res.headers["Custom"] == "1"
        assert res.headers["Location"].endswith("/20200101{0}/https://example.com/redirect-1".format(fmod))
        assert res.text == 'some\ntext'

