import re
import time
import datetime
import calendar

#=================================================================
# str <-> datetime conversion
#=================================================================

DATE_TIMESPLIT = re.compile('[^\d]')

TIMESTAMP_14 = '%Y%m%d%H%M%S'

PAD_STAMP_END = '29991231235959'



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

    dt = datetime.datetime(*map(int, nums))
    return dt

def datetime_to_timestamp(dt):
    """
    >>> datetime_to_timestamp(datetime.datetime(2013, 12, 26, 10, 11, 12))
    '20131226101112'
    """

    return dt.strftime(TIMESTAMP_14)

def iso_date_to_timestamp(string):
    """
    >>> iso_date_to_timestamp('2013-12-26T10:11:12Z')
    '20131226101112'

    >>> iso_date_to_timestamp('2013-12-26T10:11:12')
    '20131226101112'
     """

    return datetime_to_timestamp(iso_date_to_datetime(string))


# default pad is end of range for compatibility
def pad_timestamp(string, pad_str = PAD_STAMP_END):
    """
    >>> pad_timestamp('20')
    '20991231235959'

    >>> pad_timestamp('2014')
    '20141231235959'

    >>> pad_timestamp('20141011')
    '20141011235959'

    >>> pad_timestamp('201410110010')
    '20141011001059'
     """

    str_len = len(string)
    pad_len = len(pad_str)

    return string if str_len >= pad_len else string + pad_str[str_len:]


def timestamp_to_datetime(string):
    """
    >>> timestamp_to_datetime('20131226095010')
    time.struct_time(tm_year=2013, tm_mon=12, tm_mday=26, tm_hour=9, tm_min=50, tm_sec=10, tm_wday=3, tm_yday=360, tm_isdst=-1)

    >>> timestamp_to_datetime('2014')
    time.struct_time(tm_year=2014, tm_mon=12, tm_mday=31, tm_hour=23, tm_min=59, tm_sec=59, tm_wday=2, tm_yday=365, tm_isdst=-1)
    """

    # Default pad to end of range for comptability
    return time.strptime(pad_timestamp(string), TIMESTAMP_14)


def timestamp_to_sec(string):
    """
    >>> timestamp_to_sec('20131226095010')
    1388051410

    >>> timestamp_to_sec('2014')
    1420070399
    """

    return calendar.timegm(timestamp_to_datetime(string))


if __name__ == "__main__":
    import doctest
    doctest.testmod()
