import xml.etree.ElementTree as ET
from contextlib import closing
from io import BytesIO, StringIO
import json

from pywb.webagg.utils import StreamIter
import re

EXT_INF = re.compile('#EXT-X-STREAM-INF:(?:.*[,])?BANDWIDTH=([\d]+)')


# ============================================================================
class RewriteDASHMixin(object):
    def handle_custom_rewrite(self, rewritten_headers, stream, urlrewriter, mod, env):
        if rewritten_headers.status_headers.get_header('Content-Type') == 'application/dash+xml':
            stream = self._decoding_stream(rewritten_headers, stream)
            stream, _ = self.rewrite_dash(stream)
            rewritten_headers.status_headers.remove_header('content-length')
            return (rewritten_headers.status_headers, StreamIter(stream), True)

        elif rewritten_headers.status_headers.get_header('Content-Type') == 'application/x-mpegURL':
            stream = self._decoding_stream(rewritten_headers, stream)
            stream = self.rewrite_m3u8(stream)
            rewritten_headers.status_headers.remove_header('content-length')
            return (rewritten_headers.status_headers, StreamIter(stream), True)

        return (super(RewriteDASHMixin, self).
                handle_custom_rewrite(rewritten_headers, stream, urlrewriter, mod, env))

    @classmethod
    def rewrite_dash(cls, stream):
        ET.register_namespace('', 'urn:mpeg:dash:schema:mpd:2011')
        namespaces = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}

        buff_io = BytesIO()
        with closing(stream) as fh:
            while True:
                buff = fh.read()
                if not buff:
                    break

                buff_io.write(buff)

        buff_io.seek(0)
        tree = ET.ElementTree()
        tree.parse(buff_io)

        root = tree.getroot()

        best_ids = []

        for period in root.findall('mpd:Period', namespaces):
            for adaptset in period.findall('mpd:AdaptationSet', namespaces):

                best = None
                for repres in adaptset.findall('mpd:Representation', namespaces):
                    bandwidth = int(repres.get('bandwidth', '0'))
                    if not best or bandwidth > int(best.get('bandwidth', '0')):
                        best = repres

                if best:
                    best_ids.append(best.get('id'))

                for repres in adaptset.findall('mpd:Representation', namespaces):
                    if repres != best:
                        adaptset.remove(repres)

        string_io = StringIO()
        tree.write(string_io, encoding='unicode', xml_declaration=True)
        buff_io = BytesIO()
        buff_io.write(string_io.getvalue().encode('utf-8'))
        buff_io.seek(0)
        return buff_io, best_ids

    @classmethod
    def rewrite_m3u8(cls, stream):
        buff = stream.read()

        lines = buff.decode('utf-8').split('\n')
        best = None
        indexes = []
        count = 0
        best_index = None

        for line in lines:
            m = EXT_INF.match(line)
            if m:
                indexes.append(count)
                bandwidth = int(m.group(1))
                if not best or bandwidth > best:
                    best = bandwidth
                    best_index = count

            count = count + 1

        if indexes and best_index is not None:
            indexes.remove(best_index)

        for index in reversed(indexes):
            del lines[index + 1]
            del lines[index]

        buff_io = BytesIO()
        buff_io.write('\n'.join(lines).encode('utf-8'))
        buff_io.seek(0)
        return buff_io

