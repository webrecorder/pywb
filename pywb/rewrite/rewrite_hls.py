import re
from io import BytesIO

from pywb.rewrite.content_rewriter import BufferedRewriter


# ============================================================================
class RewriteHLS(BufferedRewriter):
    EXT_INF = re.compile('#EXT-X-STREAM-INF:(?:.*[,])?BANDWIDTH=([\d]+)')

    def rewrite_stream(self, stream):
        buff = stream.read()

        lines = buff.decode('utf-8').split('\n')
        best = None
        indexes = []
        count = 0
        best_index = None

        for line in lines:
            m = self.EXT_INF.match(line)
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

