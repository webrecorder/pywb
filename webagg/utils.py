import re
import six
import string
import time

from pywb.utils.timeutils import timestamp_to_http_date
from pywb.utils.wbexception import BadRequestException

LINK_SPLIT = re.compile(',\s*(?=[<])')
LINK_SEG_SPLIT = re.compile(';\s*')
LINK_URL = re.compile('<(.*)>')
LINK_PROP = re.compile('([\w]+)="([^"]+)')

BUFF_SIZE = 8192


#=============================================================================
class MementoException(BadRequestException):
    pass


#=============================================================================
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

    @staticmethod
    def make_timemap_memento_link(cdx, datetime=None, rel='memento', end=',\n'):
        url = cdx.get('load_url')
        if not url:
            url = 'file://{0}:{1}:{2}'.format(cdx.get('filename'), cdx.get('offset'), cdx.get('length'))

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
            return

        # first memento link
        yield MementoUtils.make_timemap_memento_link(first_cdx, datetime=from_date)

        prev_cdx = None

        for cdx in cdx_iter:
            if prev_cdx:
                yield MementoUtils.make_timemap_memento_link(prev_cdx)

            prev_cdx = cdx

        # last memento link, if any
        if prev_cdx:
            yield MementoUtils.make_timemap_memento_link(prev_cdx, end='\n')

    @staticmethod
    def make_link(url, type):
        return '<{0}>; rel="{1}"'.format(url, type)


#=============================================================================
class ParamFormatter(string.Formatter):
    def __init__(self, params, name='', prefix='param.'):
        self.params = params
        self.prefix = prefix
        self.name = name

    def get_value(self, key, args, kwargs):
        # First, try the named param 'param.{name}.{key}'
        if self.name:
            named_key = self.prefix + self.name + '.' + key
            value = self.params.get(named_key)
            if value is not None:
                return value

        # Then, try 'param.{key}'
        named_key = self.prefix + key
        value = self.params.get(named_key)
        if value is not None:
            return value

        # default to just '{key}'
        value = kwargs.get(key, '')
        return value


#=============================================================================
def res_template(template, params):
    formatter = params.get('_formatter')
    if not formatter:
        formatter = ParamFormatter(params)

    res = formatter.format(template, url=params['url'])

    return res


#=============================================================================
class ReadFullyStream(object):
    def __init__(self, stream):
        self.stream = stream

    def read(self, *args, **kwargs):
        try:
            return self.stream.read(*args, **kwargs)
        except:
            self.mark_incomplete()
            raise

    def readline(self, *args, **kwargs):
        try:
            return self.stream.readline(*args, **kwargs)
        except:
            self.mark_incomplete()
            raise

    def mark_incomplete(self):
        if (hasattr(self.stream, '_fp') and
            hasattr(self.stream._fp, 'mark_incomplete')):
            self.stream._fp.mark_incomplete()

    def close(self):
        try:
            while True:
                buff = self.stream.read(BUFF_SIZE)
                time.sleep(0)
                if not buff:
                    break

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.mark_incomplete()
        finally:
            self.stream.close()


#=============================================================================
class StreamIter(six.Iterator):
    def __init__(self, stream, header1=None, header2=None, size=8192):
        self.stream = stream
        self.header1 = header1
        self.header2 = header2
        self.size = size

    def __iter__(self):
        return self

    def __next__(self):
        if self.header1:
            header = self.header1
            self.header1 = None
            return header
        elif self.header2:
            header = self.header2
            self.header2 = None
            return header

        data = self.stream.read(self.size)
        if data:
            return data

        self.close()
        raise StopIteration

    def close(self):
        if not self.stream:
            return

        try:
            self.stream.close()
            self.stream = None
        except Exception:
            pass


