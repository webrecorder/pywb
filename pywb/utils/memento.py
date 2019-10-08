import re
import six

from warcio.timeutils import timestamp_to_http_date, http_date_to_timestamp

from pywb.utils.wbexception import BadRequestException


LINK_SPLIT = re.compile(',\s*(?=[<])')
LINK_SEG_SPLIT = re.compile(';\s*')
LINK_URL = re.compile('<(.*)>')
LINK_PROP = re.compile('([\w]+)="([^"]+)')

FIND_DT = re.compile('datetime=\"([^\"]+)\"')


#=============================================================================
class MementoException(BadRequestException):
    pass


#=============================================================================
class MementoUtils(object):
    @classmethod
    def parse_links(cls, link_header, def_name='timemap'):
        links = LINK_SPLIT.split(link_header)
        results = {}
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
    def make_timemap_memento_link(cls, cdx, datetime=None, rel='memento', end=',\n', memento_format=None):
        """Creates a memento link string for a timemap

        :param dict cdx: The cdx object
        :param str|None datetime: The datetime
        :param str rel: The rel type
        :param str end: Optional string appended to the end of the created link string
        :param str|None memento_format: Optional string used to format the URL
        :return: A memento link string
        :rtype: str
        """
        url = cdx.get('url')
        if not url:
            url = 'file://{0}:{1}:{2}'.format(cdx.get('filename'), cdx.get('offset'), cdx.get('length'))

        if not datetime:
            datetime = timestamp_to_http_date(cdx['timestamp'])

        return cls.make_memento_link(url, rel, datetime, cdx.get('source-coll'), memento_format) + end

    @classmethod
    def make_timemap(cls, cdx_iter, params):
        prev_cdx = None
        memento_format = params.get('memento_format')

        for cdx in cdx_iter:
            if prev_cdx:
                yield cls.make_timemap_memento_link(prev_cdx, memento_format=memento_format)

            prev_cdx = cdx

        # last memento link, if any
        if prev_cdx:
            yield cls.make_timemap_memento_link(prev_cdx, end='\n', memento_format=memento_format)

    @classmethod
    def wrap_timemap_header(cls, url, timegate_url, timemap_url, timemap):
        string = cls.make_link(timemap_url, "self")
        m = FIND_DT.search(timemap)
        if m:
            string += '; from="{0}"'.format(m.group(1))

        string += ',\n'

        string += cls.make_link(timegate_url, "timegate") + ',\n'
        string += cls.make_link(url, "original") + ',\n'
        string += timemap
        return string

    @classmethod
    def make_link(cls, url, type):
        if type in ('timemap', 'self'):
            return '<{0}>; rel="{1}"; type="application/link-format"'.format(url, type)

        return '<{0}>; rel="{1}"'.format(url, type)

    @classmethod
    def make_memento_link(cls, url, type, dt, coll=None, memento_format=None):
        """Creates a memento link string

        :param str url: A URL
        :param str type: The rel type
        :param str dt: The datetime of the URL
        :param str|None coll: Optional name of a collection
        :param str|None memento_format: Optional string used to format the supplied URL
        :return: A memento link string
        :rtype: str
        """
        if memento_format:
            memento_format = memento_format.format(url=url,
                                                   timestamp=http_date_to_timestamp(dt))
        else:
            memento_format = url

        res = '<{0}>; rel="{1}"; datetime="{2}"'.format(memento_format, type, dt)
        if coll:
            res += '; collection="{0}"'.format(coll)

        return res


