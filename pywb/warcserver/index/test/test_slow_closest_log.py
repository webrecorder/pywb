import logging
from datetime import datetime, timedelta

import pytest
from mock import patch

from pywb.warcserver.index.cdxobject import CDXObject
from pywb.warcserver.index.cdxops import process_cdx, SlowClosestLog
from pywb.warcserver.index.query import CDXQuery
from pywb.warcserver.index.test.test_cdxops import cdx_ops_test_data
from pywb.warcserver.warcserver import WarcServer


# ============================================================================
URL = 'http://example.com/script.js'
KEY = 'com,example)/script.js'
NUM_CAPTURES = 50

# one capture per hour, from 20200101000000 to 20200103010000
CDX_LINES = ['{0} {1} {2} application/javascript 200 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA '
             '- - 100 {3} example.warc.gz'.format(
                 KEY, (datetime(2020, 1, 1) + timedelta(hours=i)).strftime('%Y%m%d%H%M%S'),
                 URL, i * 100)
             for i in range(NUM_CAPTURES)]

# after the last capture: every capture is scanned, with or without an early exit
CLOSEST_AFTER_ALL = '20210101000000'


def closest_lookup(closest, limit=None, **params):
    params['url'] = URL
    params['closest'] = closest
    if limit:
        params['limit'] = str(limit)

    query = CDXQuery(params)
    cdx_iter = (CDXObject(line.encode('utf-8')) for line in CDX_LINES)
    return [cdx.to_text() for cdx in process_cdx(cdx_iter, query)]


def slow_records(caplog):
    return [r for r in caplog.records if r.getMessage().startswith('slow closest lookup:')]


# ============================================================================
class TestSlowClosestLog(object):
    def setup_method(self):
        SlowClosestLog.init(None)

    def teardown_method(self):
        SlowClosestLog.init(None)

    def test_disabled_by_default(self, caplog):
        caplog.set_level(logging.DEBUG)

        assert SlowClosestLog.enabled == False

        res = closest_lookup(CLOSEST_AFTER_ALL)
        assert len(res) == NUM_CAPTURES
        assert slow_records(caplog) == []

    def test_init(self):
        for config in (None, {}, {'min_captures': 0, 'min_seconds': 0}):
            SlowClosestLog.init(config)
            assert SlowClosestLog.enabled == False

        SlowClosestLog.init({'min_captures': '1000'})
        assert SlowClosestLog.enabled == True
        assert SlowClosestLog.min_captures == 1000
        assert SlowClosestLog.min_seconds == None

        SlowClosestLog.init({'min_seconds': 2.5})
        assert SlowClosestLog.enabled == True
        assert SlowClosestLog.min_captures == None
        assert SlowClosestLog.min_seconds == 2.5

    def test_min_captures_reached(self, caplog):
        SlowClosestLog.init({'min_captures': NUM_CAPTURES})

        closest_lookup(CLOSEST_AFTER_ALL, limit=10)

        records = slow_records(caplog)
        assert len(records) == 1
        assert records[0].levelno == logging.WARNING
        assert records[0].name == 'warcserver'

        msg = records[0].getMessage()
        assert '\n' not in msg
        assert msg.startswith('slow closest lookup: key=com,example)/script.js '
                              'closest=20210101000000 scanned=50 limit=10 elapsed=')
        assert msg.endswith('s')

    def test_min_captures_not_reached(self, caplog):
        SlowClosestLog.init({'min_captures': NUM_CAPTURES + 1})

        closest_lookup(CLOSEST_AFTER_ALL)

        assert slow_records(caplog) == []

    def test_min_seconds_reached(self, caplog):
        SlowClosestLog.init({'min_seconds': 2})

        with patch('pywb.warcserver.index.cdxops.monotonic', side_effect=[100.0, 102.5]):
            closest_lookup(CLOSEST_AFTER_ALL)

        records = slow_records(caplog)
        assert len(records) == 1
        assert records[0].getMessage() == ('slow closest lookup: key=com,example)/script.js '
                                           'closest=20210101000000 scanned=50 limit=100000 '
                                           'elapsed=2.500s')

    def test_min_seconds_not_reached(self, caplog):
        SlowClosestLog.init({'min_seconds': 2, 'min_captures': NUM_CAPTURES + 1})

        with patch('pywb.warcserver.index.cdxops.monotonic', side_effect=[100.0, 101.0]):
            closest_lookup(CLOSEST_AFTER_ALL)

        assert slow_records(caplog) == []

    def test_no_captures(self, caplog):
        SlowClosestLog.init({'min_captures': 1})

        query = CDXQuery({'url': URL, 'closest': CLOSEST_AFTER_ALL})
        assert list(process_cdx(iter([]), query)) == []

        assert slow_records(caplog) == []

        SlowClosestLog.init({'min_seconds': 2})

        with patch('pywb.warcserver.index.cdxops.monotonic', side_effect=[100.0, 103.0]):
            assert list(process_cdx(iter([]), query)) == []

        assert 'scanned=0 ' in slow_records(caplog)[0].getMessage()

    def test_not_closest(self, caplog):
        SlowClosestLog.init({'min_captures': 1})

        query = CDXQuery({'url': URL})
        cdx_iter = (CDXObject(line.encode('utf-8')) for line in CDX_LINES)
        assert len(list(process_cdx(cdx_iter, query))) == NUM_CAPTURES

        assert slow_records(caplog) == []

    def test_log_is_single_line(self, caplog):
        SlowClosestLog.init({'min_captures': 1})

        closest_lookup('2020\nfake log line')

        msg = slow_records(caplog)[0].getMessage()
        assert '\n' not in msg
        assert ' closest=2020\\nfake log line scanned=50 ' in msg

    @pytest.mark.parametrize('closest,limit', [
        (CLOSEST_AFTER_ALL, None),
        ('20190101000000', 3),
        ('20200101123000', 1),
        ('20200102', 5),
        ('20200102120000', 10),
        ('2020', 100),
    ])
    def test_results_unchanged(self, closest, limit, caplog):
        expected = closest_lookup(closest, limit)

        SlowClosestLog.init({'min_captures': 1, 'min_seconds': 0.000001})
        assert closest_lookup(closest, limit) == expected
        assert len(slow_records(caplog)) == 1

    def test_aggregator(self, caplog):
        SlowClosestLog.init({'min_captures': 3})

        res = cdx_ops_test_data(url='http://iana.org/_css/2013.1/fonts/opensans-bold.ttf',
                                closest='20140126200826', limit=2)
        assert len(res) == 2

        records = slow_records(caplog)
        assert len(records) == 1
        assert records[0].getMessage().startswith(
            'slow closest lookup: key=org,iana)/_css/2013.1/fonts/opensans-bold.ttf '
            'closest=20140126200826 scanned=')

    def test_warcserver_config(self):
        WarcServer(config_file=None,
                   custom_config={'slow_closest_log': {'min_captures': 50000, 'min_seconds': 2}})

        assert SlowClosestLog.enabled == True
        assert SlowClosestLog.min_captures == 50000
        assert SlowClosestLog.min_seconds == 2

        WarcServer(config_file=None, custom_config={})
        assert SlowClosestLog.enabled == False
