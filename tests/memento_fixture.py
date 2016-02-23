import re

MEMENTO_DATETIME = 'Memento-Datetime'
ACCEPT_DATETIME = 'Accept-Datetime'
LINK = 'Link'
VARY = 'Vary'
LINK_FORMAT = 'application/link-format'

class MementoMixin(object):
    def get_links(self, resp):
        return list(map(lambda x: x.strip(), re.split(', (?![0-9])', resp.headers[LINK])))

    def make_timemap_link(self, url, coll='pywb'):
        format_ = '<http://localhost:80/{2}/timemap/*/{0}>; rel="timemap"; type="{1}"'
        return format_.format(url, LINK_FORMAT, coll)

    def make_memento_link(self, url, ts, dt, coll='pywb'):
        format_ = '<http://localhost:80/{3}/{1}/{0}>; rel="memento"; datetime="{2}"'
        return format_.format(url, ts, dt, coll)


