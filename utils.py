import re, json
from pywb.utils.canonicalize import canonicalize
from pywb.utils.timeutils import timestamp_to_sec, http_date_to_timestamp
from pywb.cdx.cdxobject import CDXObject


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
    def links_to_json(link_header, def_name='timemap', sort=False):
        results = MementoUtils.parse_links(link_header, def_name)

        #meta = MementoUtils.meta_field('timegate', results)
        #if meta:
        #    yield meta

        #meta = MementoUtils.meta_field('timemap', results)
        #if meta:
        #    yield meta

        #meta = MementoUtils.meta_field('original', results)
        #if meta:
        #    yield meta

        original = results['original']['url']
        key = canonicalize(original)

        mementos = results['mementos']
        if sort:
            mementos = sorted(mementos)

        def link_iter():
            for val in mementos:
                dt = val.get('datetime')
                if not dt:
                    continue

                ts = http_date_to_timestamp(dt)
                line = CDXObject()
                line['urlkey'] = key
                line['timestamp'] = ts
                line['url'] = original
                line['mem_rel'] = val.get('rel', '')
                line['memento_url'] = val['url']
                yield line

        return original, link_iter

    @staticmethod
    def meta_field(name, results):
        v = results.get(name)
        if v:
            c = CDXObject()
            c['key'] = '@' + name
            c['url'] = v['url']
            return c




#=================================================================
def cdx_sort_closest(closest, cdx_json):
    closest_sec = timestamp_to_sec(closest)

    def get_key(cdx):
        sec = timestamp_to_sec(cdx['timestamp'])
        return abs(closest_sec - sec)

    cdx_sorted = sorted(cdx_json, key=get_key)
    return cdx_sorted



