from contextlib import closing
from io import BytesIO, StringIO
import json

import xml.etree.ElementTree as ET

from pywb.rewrite.content_rewriter import BufferedRewriter


# ============================================================================
class RewriteDASH(BufferedRewriter):
    def rewrite_stream(self, stream):
        res_buff, best_ids = self.rewrite_dash(stream)
        return res_buff

    def rewrite_dash(self, stream):
        ET.register_namespace('', 'urn:mpeg:dash:schema:mpd:2011')
        namespaces = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}

        tree = ET.ElementTree()
        tree.parse(stream)

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


# ============================================================================
def rewrite_fb_dash(string):
    DASH_SPLIT = r'\n",dash_prefetched_representation_ids:'
    inx = string.find(DASH_SPLIT)
    if inx < 0:
        return string

    string = string[:inx]

    buff = string.encode('utf-8').decode('unicode-escape')
    buff = buff.encode('utf-8')
    io = BytesIO(buff)
    io, best_ids = RewriteDASH().rewrite_dash(io)
    string = json.dumps(io.read().decode('utf-8'))
    string = string[1:-1].replace('<', r'\x3C')

    string += DASH_SPLIT
    string += json.dumps(best_ids)
    return string

