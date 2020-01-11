from contextlib import closing
from io import BytesIO
import json

import xml.etree.ElementTree as ET

from pywb.rewrite.content_rewriter import BufferedRewriter


# ============================================================================
class RewriteDASH(BufferedRewriter):
    def rewrite_stream(self, stream, rwinfo):
        res_buff, best_ids = self.rewrite_dash(stream, rwinfo)
        return res_buff

    def rewrite_dash(self, stream, rwinfo):
        max_resolution, max_bandwidth = self._get_adaptive_metadata(rwinfo)
        ET.register_namespace('', 'urn:mpeg:dash:schema:mpd:2011')
        namespaces = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}

        tree = ET.ElementTree()
        tree.parse(stream)

        root = tree.getroot()

        best_ids = []

        for period in root.findall('mpd:Period', namespaces):
            for adaptset in period.findall('mpd:AdaptationSet', namespaces):
                best = None
                best_resolution = 0
                best_bandwidth = 0

                for repres in adaptset.findall('mpd:Representation', namespaces):
                    curr_resolution = int(repres.get('width', '0')) * int(repres.get('height', '0'))
                    curr_bandwidth = int(repres.get('bandwidth', 0))
                    if curr_resolution and max_resolution:
                        if curr_resolution <= max_resolution and curr_resolution > best_resolution:
                            best_resolution = curr_resolution
                            best_bandwidth = curr_bandwidth
                            best = repres
                    elif curr_bandwidth <= max_bandwidth and curr_bandwidth > best_bandwidth:
                        best_resolution = curr_resolution
                        best_bandwidth = curr_bandwidth
                        best = repres

                if best is not None:
                    best_ids.append(best.get('id'))

                for repres in adaptset.findall('mpd:Representation', namespaces):
                    if repres != best:
                        adaptset.remove(repres)

        buff_io = BytesIO()
        tree.write(buff_io, encoding='UTF-8', xml_declaration=True)
        buff_io.seek(0)
        return buff_io, best_ids


# ============================================================================
def rewrite_fb_dash(string, *args):
    DASH_SPLITS = [r'\n",dash_prefetched_representation_ids:', r'\n","dash_prefetched_representation_ids":']

    inx = -1
    split = None
    for split in DASH_SPLITS:
        inx = string.find(split)
        if inx >= 0:
            break

    if inx < 0:
        return

    string = string[:inx]

    buff = string.encode('utf-8').decode('unicode-escape')
    buff = buff.replace('\\/', '/')
    buff = buff.encode('utf-8')
    io = BytesIO(buff)
    io, best_ids = RewriteDASH().rewrite_dash(io, None)
    buff = io.read().decode('utf-8')
    string = json.dumps(buff)
    string = string[1:-1].replace('<', r'\x3C')

    string += split
    string += json.dumps(best_ids)
    return string

