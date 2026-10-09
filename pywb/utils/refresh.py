import re


# =============================================================================
# Parsing of the Refresh header and <meta http-equiv="refresh"> content values,
# loosely following the HTML spec's "shared declarative refresh steps":
#   <delay>[;|,] [url=]['|"]<url>['|"]
REFRESH_PREFIX_REGEX = re.compile(r'\s*([\d.]+)(?:\s*[;,]\s*|\s+|$)(?:url\s*=\s*)?',
                                  re.IGNORECASE)


def _find_refresh_url(value):
    """Return (delay, start, end) of the url in a refresh value,
    or None if the value has no url
    """
    if not value:
        return None

    m = REFRESH_PREFIX_REGEX.match(value)
    if not m:
        return None

    delay = int(m.group(1).split('.', 1)[0] or 0)

    start = m.end()
    end = len(value)

    if start < end and value[start] in ('"', "'"):
        quote = value[start]
        start += 1
        inx = value.find(quote, start)
        if inx >= 0:
            end = inx

    while end > start and value[end - 1].isspace():
        end -= 1

    if start >= end:
        return None

    return delay, start, end


def parse_refresh(value):
    """Return (delay, url) from a refresh value, or None if the value has no url

    >>> parse_refresh('0; url=http://example.com/')
    (0, 'http://example.com/')

    >>> parse_refresh("5;URL='/path/'")
    (5, '/path/')

    >>> parse_refresh('1.5, http://example.com/')
    (1, 'http://example.com/')

    >>> parse_refresh('10')

    >>> parse_refresh('0; url=')
    """
    res = _find_refresh_url(value)
    if not res:
        return None

    delay, start, end = res
    return delay, value[start:end]


def rewrite_refresh(value, rewrite_url):
    """Return the refresh value with its url replaced by rewrite_url(url)

    >>> rewrite_refresh('0; url="http://example.com/"', lambda url: '/web/' + url)
    '0; url="/web/http://example.com/"'

    >>> rewrite_refresh('text/html; charset=utf-8', lambda url: '/web/' + url)
    'text/html; charset=utf-8'
    """
    res = _find_refresh_url(value)
    if not res:
        return value

    _, start, end = res
    return value[:start] + rewrite_url(value[start:end]) + value[end:]
