from pywb.utils.canonicalize import canonicalize
from pywb.cdx.cdxobject import CDXObject, URLKEY, ORIGINAL
from pywb.warc.cdxindexer import CDXJ

import os
import shutil


#=============================================================================
class MigrateCDX(object):
    def __init__(self, dir_):
        self.cdx_dir = dir_

    def iter_cdx_files(self):
        for root, dirs, files in os.walk(self.cdx_dir):
            for filename in files:
                if filename.endswith('.cdx'):
                    full_path = os.path.join(root, filename)
                    yield full_path

    def count_cdx(self):
        count = 0
        for x in self.iter_cdx_files():
            count += 1
        return count

    def convert_to_cdxj(self):
        cdxj_writer = CDXJ()
        for filename in self.iter_cdx_files():
            outfile = filename + 'j'

            print('Converting {0} -> {1}'.format(filename, outfile))

            with open(outfile + '.tmp', 'w+') as out:
                with open(filename, 'rb') as fh:
                    for line in fh:
                        if line.startswith(b' CDX'):
                            continue
                        cdx = CDXObject(line)
                        cdx[URLKEY] = canonicalize(cdx[ORIGINAL])
                        cdxj_writer.write_cdx_line(out, cdx, cdx['filename'])

            shutil.move(outfile + '.tmp', outfile)
            os.remove(filename)


