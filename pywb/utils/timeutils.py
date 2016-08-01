"""
utility functions for converting between
datetime, iso date and 14-digit timestamp
"""

import re
import time
import datetime
import calendar
from six.moves import map
from email.utils import parsedate, formatdate

#=================================================================
# str <-> datetime conversion
#=================================================================

DATE_TIMESPLIT = re.compile(r'[^\d]')

TIMESTAMP_14 = '%Y%m%d%H%M%S'
ISO_DT = '%Y-%m-%dT%H:%M:%SZ'

PAD_14_DOWN = '10000101000000'
PAD_14_UP =   '29991231235959'
PAD_6_UP =    '299912'


def iso_date_to_datetime(string):
    """
    >>> iso_date_to_datetime('2013-12-26T10:11:12Z')
    datetime.datetime(2013, 12, 26, 10, 11, 12)

    >>> iso_date_to_datetime('2013-12-26T10:11:12Z')
    datetime.datetime(2013, 12, 26, 10, 11, 12)
     """

    nums = DATE_TIMESPLIT.split(string)
    if nums[-1] == '':
        nums = nums[:-1]

    the_datetime = datetime.datetime(*map(int, nums))
    return the_datetime


def http_date_to_datetime(string):
    """
    >>> http_date_to_datetime('Thu, 26 Dec 2013 09:50:10 GMT')
    datetime.datetime(2013, 12, 26, 9, 50, 10)
    """
    return datetime.datetime(*parsedate(string)[:6])


def datetime_to_http_date(the_datetime):
    """
    >>> datetime_to_http_date(datetime.datetime(2013, 12, 26, 9, 50, 10))
    'Thu, 26 Dec 2013 09:50:10 GMT'

    # Verify inverses
    >>> x = 'Thu, 26 Dec 2013 09:50:10 GMT'
    >>> datetime_to_http_date(http_date_to_datetime(x)) == x
    True
    """
    timeval = calendar.timegm(the_datetime.utctimetuple())
    return formatdate(timeval=timeval,
                      localtime=False,
                      usegmt=True)


def datetime_to_iso_date(the_datetime):
    """
    >>> datetime_to_iso_date(datetime.datetime(2013, 12, 26, 10, 11, 12))
    '2013-12-26T10:11:12Z'

    >>> datetime_to_iso_date( datetime.datetime(2013, 12, 26, 10, 11, 12))
    '2013-12-26T10:11:12Z'
    """

    return the_datetime.strftime(ISO_DT)


def datetime_to_timestamp(the_datetime):
    """
    >>> datetime_to_timestamp(datetime.datetime(2013, 12, 26, 10, 11, 12))
    '20131226101112'
    """

    return the_datetime.strftime(TIMESTAMP_14)


def timestamp_now():
    """
    >>> len(timestamp_now())
    14
    """
    return datetime_to_timestamp(datetime.datetime.utcnow())


def timestamp20_now():
    """
    Create 20-digit timestamp, useful to timestamping temp files

    >>> n = timestamp20_now()
    >>> timestamp20_now() >= n
    True

    >>> len(n)
    20

    """
    now = datetime.datetime.utcnow()
    return now.strftime('%Y%m%d%H%M%S%f')


def iso_date_to_timestamp(string):
    """
    >>> iso_date_to_timestamp('2013-12-26T10:11:12Z')
    '20131226101112'

    >>> iso_date_to_timestamp('2013-12-26T10:11:12')
    '20131226101112'
     """

    return datetime_to_timestamp(iso_date_to_datetime(string))

def timestamp_to_iso_date(string):
    """
    >>> timestamp_to_iso_date('20131226101112')
    '2013-12-26T10:11:12Z'

    >>> timestamp_to_iso_date('20131226101112')
    '2013-12-26T10:11:12Z'
    """


    return datetime_to_iso_date(timestamp_to_datetime(string))


def http_date_to_timestamp(string):
    """
    >>> http_date_to_timestamp('Thu, 26 Dec 2013 09:50:00 GMT')
    '20131226095000'

    >>> http_date_to_timestamp('Sun, 26 Jan 2014 20:08:04 GMT')
    '20140126200804'
    """
    return datetime_to_timestamp(http_date_to_datetime(string))


# pad to certain length (default 6)
def pad_timestamp(string, pad_str=PAD_6_UP):
    """
    >>> pad_timestamp('20')
    '209912'

    >>> pad_timestamp('2014')
    '201412'

    >>> pad_timestamp('20141011')
    '20141011'

    >>> pad_timestamp('201410110010')
    '201410110010'
     """

    str_len = len(string)
    pad_len = len(pad_str)

    if str_len < pad_len:
        string = string + pad_str[str_len:]

    return string


def timestamp_to_datetime(string):
    """
    # >14-digit -- rest ignored
    >>> timestamp_to_datetime('2014122609501011')
    datetime.datetime(2014, 12, 26, 9, 50, 10)

    # 14-digit
    >>> timestamp_to_datetime('20141226095010')
    datetime.datetime(2014, 12, 26, 9, 50, 10)

    # 13-digit padding
    >>> timestamp_to_datetime('2014122609501')
    datetime.datetime(2014, 12, 26, 9, 50, 59)

    # 12-digit padding
    >>> timestamp_to_datetime('201412260950')
    datetime.datetime(2014, 12, 26, 9, 50, 59)

    # 11-digit padding
    >>> timestamp_to_datetime('20141226095')
    datetime.datetime(2014, 12, 26, 9, 59, 59)

    # 10-digit padding
    >>> timestamp_to_datetime('2014122609')
    datetime.datetime(2014, 12, 26, 9, 59, 59)

    # 9-digit padding
    >>> timestamp_to_datetime('201412260')
    datetime.datetime(2014, 12, 26, 23, 59, 59)

    # 8-digit padding
    >>> timestamp_to_datetime('20141226')
    datetime.datetime(2014, 12, 26, 23, 59, 59)

    # 7-digit padding
    >>> timestamp_to_datetime('2014122')
    datetime.datetime(2014, 12, 31, 23, 59, 59)

    # 6-digit padding
    >>> timestamp_to_datetime('201410')
    datetime.datetime(2014, 10, 31, 23, 59, 59)

    # 5-digit padding
    >>> timestamp_to_datetime('20141')
    datetime.datetime(2014, 12, 31, 23, 59, 59)

    # 4-digit padding
    >>> timestamp_to_datetime('2014')
    datetime.datetime(2014, 12, 31, 23, 59, 59)

    # 3-digit padding
    >>> timestamp_to_datetime('201')
    datetime.datetime(2019, 12, 31, 23, 59, 59)

    # 2-digit padding
    >>> timestamp_to_datetime('20')
    datetime.datetime(2099, 12, 31, 23, 59, 59)

    # 1-digit padding
    >>> timestamp_to_datetime('2')
    datetime.datetime(2999, 12, 31, 23, 59, 59)

    # 1-digit out-of-range padding
    >>> timestamp_to_datetime('3')
    datetime.datetime(2999, 12, 31, 23, 59, 59)

    # 0-digit padding
    >>> timestamp_to_datetime('')
    datetime.datetime(2999, 12, 31, 23, 59, 59)

    # bad month
    >>> timestamp_to_datetime('20131709005601')
    datetime.datetime(2013, 12, 9, 0, 56, 1)

    # all out of range except minutes
    >>> timestamp_to_datetime('40001965252477')
    datetime.datetime(2999, 12, 31, 23, 24, 59)

    # not a number!
    >>> timestamp_to_datetime('2010abc')
    datetime.datetime(2010, 12, 31, 23, 59, 59)

    """

    # pad to 6 digits
    string = pad_timestamp(string, PAD_6_UP)

    def clamp(val, min_, max_):
        try:
            val = int(val)
            val = max(min_, min(val, max_))
            return val
        except:
            return max_

    def extract(string, start, end, min_, max_):
        if len(string) >= end:
            return clamp(string[start:end], min_, max_)
        else:
            return max_

    # now parse, clamp to boundary
    year = extract(string, 0, 4, 1900, 2999)
    month = extract(string, 4, 6, 1, 12)
    day = extract(string, 6, 8, 1, calendar.monthrange(year, month)[1])
    hour = extract(string, 8, 10, 0, 23)
    minute = extract(string, 10, 12, 0, 59)
    second = extract(string, 12, 14, 0, 59)

    return datetime.datetime(year=year,
                             month=month,
                             day=day,
                             hour=hour,
                             minute=minute,
                             second=second)

    #return time.strptime(pad_timestamp(string), TIMESTAMP_14)


def timestamp_to_sec(string):
    """
    >>> timestamp_to_sec('20131226095010')
    1388051410

    # rounds to end of 2014
    >>> timestamp_to_sec('2014')
    1420070399
    """

    return calendar.timegm(timestamp_to_datetime(string).utctimetuple())


def sec_to_timestamp(secs):
    """
    >>> sec_to_timestamp(1388051410)
    '20131226095010'

    >>> sec_to_timestamp(1420070399)
    '20141231235959'
    """

    return datetime_to_timestamp(datetime.datetime.utcfromtimestamp(secs))


def timestamp_to_http_date(string):
    """
    >>> timestamp_to_http_date('20131226095000')
    'Thu, 26 Dec 2013 09:50:00 GMT'

    >>> timestamp_to_http_date('20140126200804')
    'Sun, 26 Jan 2014 20:08:04 GMT'
    """
    return datetime_to_http_date(timestamp_to_datetime(string))


if __name__ == "__main__":
    import doctest
    doctest.testmod()
