import re
from io import BytesIO

from pywb.rewrite.content_rewriter import BufferedRewriter


# ============================================================================
class RewriteHLS(BufferedRewriter):
    EXT_INF = re.compile('#EXT-X-STREAM-INF:(?:.*[,])?BANDWIDTH=([\d]+)')
    EXT_RESOLUTION = re.compile('RESOLUTION=([\d]+)x([\d]+)')

    def rewrite_stream(self, stream, rwinfo):
        max_resolution, max_bandwidth = self._get_adaptive_metadata(rwinfo)

        buff = stream.read()

        lines = buff.decode('utf-8').split('\n')
        indexes = []
        count = 0
        best_index = None

        best_bandwidth = 0
        best_resolution = 0

        for line in lines:
            m = self.EXT_INF.match(line)
            if m:
                indexes.append(count)
                curr_bandwidth = int(m.group(1))

                # resolution
                m2 = self.EXT_RESOLUTION.search(line)
                if m2:
                    curr_resolution = int(m2.group(1)) * int(m2.group(2))
                else:
                    curr_resolution = 0

                if max_resolution and curr_resolution:
                    if curr_resolution > best_resolution and curr_resolution <= max_resolution:
                        best_resolution = curr_resolution
                        best_bandwidth = curr_bandwidth
                        best_index = count

                elif curr_bandwidth > best_bandwidth and curr_bandwidth <= max_bandwidth:
                    best_resolution = curr_resolution
                    best_bandwidth = curr_bandwidth
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

