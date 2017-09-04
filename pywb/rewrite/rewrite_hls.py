import re
from io import BytesIO

from pywb.rewrite.content_rewriter import BufferedRewriter


# ============================================================================
class RewriteHLS(BufferedRewriter):
    EXT_INF = re.compile('#EXT-X-STREAM-INF:(?:.*[,])?BANDWIDTH=([\d]+)')

    def rewrite_stream(self, stream, rwinfo):
        max_bandwidth = self._get_metadata(rwinfo, 'adaptive_max_bandwidth', 10000000000)
        buff = stream.read()

        lines = buff.decode('utf-8').split('\n')
        best = 0
        indexes = []
        count = 0
        best_index = None

        for line in lines:
            m = self.EXT_INF.match(line)
            if m:
                indexes.append(count)
                bandwidth = int(m.group(1))
                if bandwidth > best and bandwidth <= max_bandwidth:
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

