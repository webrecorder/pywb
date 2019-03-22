import re

from warcio.timeutils import timestamp_to_http_date

from pywb.utils.wbexception import BadRequestException

LINK_SPLIT = re.compile(',\s*(?=[<])')
LINK_SEG_SPLIT = re.compile(';\s*')
LINK_URL = re.compile('<(.*)>')
LINK_PROP = re.compile('([\w]+)="([^"]+)')

FIND_DT = re.compile('datetime=\"([^\"]+)\"')


# =============================================================================
class MementoException(BadRequestException):
    pass


# =============================================================================
class MementoUtils(object):
    @classmethod
    def parse_links(cls, link_header, def_name='timemap'):
        links = LINK_SPLIT.split(link_header)
        results = dict()
        mementos = []

        for link in links:
            props = LINK_SEG_SPLIT.split(link)
            m = LINK_URL.match(props[0])
            if not m:
                raise MementoException('Invalid Link Url: ' + props[0])

            result = dict(url=m.group(1))
            key = ''
            is_mem = False

            for prop in props[1:]:
                m = LINK_PROP.match(prop)
                if not m:
                    raise MementoException('Invalid prop ' + prop)

                name = m.group(1)
                value = m.group(2)

                if name == 'rel':
                    if 'memento' in value:
                        is_mem = True
                        result[name] = value
                    elif value == 'self':
                        key = def_name
                    else:
                        key = value
                else:
                    result[name] = value

            if key:
                results[key] = result
            elif is_mem:
                mementos.append(result)

        results['mementos'] = mementos
        return results

    @classmethod
    def make_timemap_memento_link(cls, cdx, datetime=None, rel='memento', end=',\n'):
        url = cdx.get('url')
        if not url:
            url = 'file://{0}:{1}:{2}'.format(cdx.get('filename'), cdx.get('offset'), cdx.get('length'))

        if not datetime:
            datetime = timestamp_to_http_date(cdx['timestamp'])

        return cls.make_memento_link(url, rel, datetime, cdx.get('source-coll')) + end

    @classmethod
    def make_timemap(cls, cdx_iter):
        prev_cdx = None

        for cdx in cdx_iter:
            if prev_cdx:
                yield cls.make_timemap_memento_link(prev_cdx)

            prev_cdx = cdx

        # last memento link, if any
        if prev_cdx:
            yield cls.make_timemap_memento_link(prev_cdx, end='\n')

    @classmethod
    def wrap_timemap_header(cls, url, timegate_url, timemap_url, timemap):
        header = [cls.make_link(timemap_url, "self")]
        m = FIND_DT.search(timemap)
        if m:
            header.append('; from="{0}"'.format(m.group(1)))

        header.append(',\n')

        header.append(cls.make_link(timegate_url, "timegate") + ',\n')
        header.append(cls.make_link(url, "original") + ',\n')
        header.append(timemap)
        return ''.join(header)

    @classmethod
    def make_link(cls, url, type_):
        if type_ in ('timemap', 'self'):
            return '<{0}>; rel="{1}"; type="application/link-format"'.format(url, type_)

        return '<{0}>; rel="{1}"'.format(url, type_)

    @classmethod
    def make_memento_link(cls, url, type_, dt, coll=None):
        res = '<{0}>; rel="{1}"; datetime="{2}"'.format(url, type_, dt)
        if coll:
            return res + '; collection="{0}"'.format(coll)

        return res
