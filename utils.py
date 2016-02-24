import re
import six

from pywb.utils.timeutils import timestamp_to_http_date


LINK_SPLIT = re.compile(',\s*(?=[<])')
LINK_SEG_SPLIT = re.compile(';\s*')
LINK_URL = re.compile('<(.*)>')
LINK_PROP = re.compile('([\w]+)="([^"]+)')


#=================================================================
class MementoUtils(object):
    @staticmethod
    def parse_links(link_header, def_name='timemap'):
        links = LINK_SPLIT.split(link_header)
        results = {}
        mementos = []

        for link in links:
            props = LINK_SEG_SPLIT.split(link)
            m = LINK_URL.match(props[0])
            if not m:
                raise Exception('Invalid Link Url: ' + props[0])

            result = dict(url=m.group(1))
            key = ''
            is_mem = False

            for prop in props[1:]:
                m = LINK_PROP.match(prop)
                if not m:
                    raise Exception('Invalid prop ' + prop)

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

    @staticmethod
    def make_timemap_memento_link(cdx, datetime=None, rel='memento', end=',\n'):

        url = cdx.get('load_url')
        if not url:
            url = 'filename://' + cdx.get('filename')

        memento = '<{0}>; rel="{1}"; datetime="{2}"; src="{3}"' + end

        if not datetime:
            datetime = timestamp_to_http_date(cdx['timestamp'])

        return memento.format(url, rel, datetime, cdx.get('source', ''))


    @staticmethod
    def make_timemap(cdx_iter):
        # get first memento as it'll be used for 'from' field
        try:
            first_cdx = six.next(cdx_iter)
            from_date = timestamp_to_http_date(first_cdx['timestamp'])
        except StopIteration:
            first_cdx = None

        # first memento link
        yield MementoUtils.make_timemap_memento_link(first_cdx, datetime=from_date)

        prev_cdx = None

        for cdx in cdx_iter:
            if prev_cdx:
                yield MementoUtils.make_timemap_memento_link(prev_cdx)

            prev_cdx = cdx

        # last memento link, if any
        if prev_cdx:
            yield MementoUtils.make_timemap_memento_link(prev_cdx, end='')
