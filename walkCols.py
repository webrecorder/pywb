import json

from warcio.archiveiterator import ArchiveIterator
from warcio.warcwriter import WARCWriter
from glob import glob
from collections import Counter, defaultdict
import surt
import requests
import shutil
from os.path import splitext

def walkWarcs():
    c = Counter()
    for it in glob('/home/john/PycharmProjects/pywb/realCols/collections/AllWarcs/archive/*'):
        with open(it, 'rb') as stream:
            for record in ArchiveIterator(stream):
                # print(record.rec_type)
                if record.rec_type == 'response':
                    ct = record.http_headers.get_header('Content-Type')
                    if ct is not None:
                        if 'text/html' in ct or 'html' in ct:
                            c[record.rec_headers.get_header('WARC-Target-URI')] += 1
    with open('uris.txt', 'w') as out:
        for k, v in sorted(c.items(), key=lambda x: x[1]):
            print(k, v)
            out.write('%s\n' % k)


want = {'edu,odu', 'org,dlib', 'com,npmjs', 'is,object',
        'com,github', 'edu,odu,cs', 'com,twitter', 'com,matkelly', 'com,bluebirdjs',
        'com,blogspot,ws-dl', 'org,freemasonstreet'

        }

ilyaDl = ["https://webrecorder.io/ilya/4thpshd/$download", "https://webrecorder.io/ilya/aittest/$download",
          "https://webrecorder.io/ilya/articles/$download", "https://webrecorder.io/ilya/augmentation-demo/$download",
          "https://webrecorder.io/ilya/demo/$download", "https://webrecorder.io/ilya/demo-test-2/$download",
          "https://webrecorder.io/ilya/demopda/$download", "https://webrecorder.io/ilya/dronepapers/$download",
          "https://webrecorder.io/ilya/forbes-articles/$download", "https://webrecorder.io/ilya/googleplus/$download",
          "https://webrecorder.io/ilya/hungerforjustice/$download", "https://webrecorder.io/ilya/ia/$download",
          "https://webrecorder.io/ilya/new-demo/$download", "https://webrecorder.io/ilya/org-stats/$download",
          "https://webrecorder.io/ilya/owt/$download", "https://webrecorder.io/ilya/press/$download",
          "https://webrecorder.io/ilya/snapshots/$download", "https://webrecorder.io/ilya/test-perf/$download",
          "https://webrecorder.io/ilya/tweets/$download", "https://webrecorder.io/ilya/twittertest/$download",
          "https://webrecorder.io/ilya/ustream/$download", "https://webrecorder.io/ilya/warc-with-cookies/$download",
          "https://webrecorder.io/ilya/washpost/$download", "https://webrecorder.io/ilya/yt/$download"]


# https://webrecorder.io/jberlin/boo/$download
# https://webrecorder.io/jberlin/what-happens/20170303055453/https://n0tan3rd.github.io/replay_test/
# https://webrecorder.io/jberlin/what-happens/20170303181234/https://n0tan3rd.github.io/replay_test/oneBundle
# https://webrecorder.io/jberlin/boo/20170411233921/http://singlepageappbook.com/goal.html
# https://webrecorder.io/jberlin/boo/20170411233808/https://reacttraining.com/react-router/web/guides/quick-start

def something():
    it = defaultdict(list)
    with open('uris.txt', 'r') as uris:
        for l in uris:
            l = l.rstrip()
            domain, rest = surt.surt(l).split(')/')
            it[domain].append(l)
    for k, v in sorted(it.items(), key=lambda x: len(x[0])):
        print(k, v)


no_include = ['http://www.w3.org','http://t.teads.tv/track?']

from itertools import zip_longest # for Python 3.x
#from six.moves import zip_longest # for both (uses the six compat library)

def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)

if __name__ == '__main__':
        c = 0
        for it in grouper(7,glob('/home/john/PycharmProjects/pywb/realCols/collections/AllWarcs/archive/*')):
            with open('singleWarc-%s.warc.gz'%c, 'wb') as out:
                writter = WARCWriter(out, gzip=True)
                for it2 in it:
                    with open(it2, 'rb') as stream:
                        for record in ArchiveIterator(stream):
                             writter.write_record(record)
            c += 1
            print(it)
    # with open('singleWarc.warc.gz','wb') as out:
    #     writter = WARCWriter(out, gzip=True)
    #     for it in glob('/home/john/PycharmProjects/pywb/realCols/collections/AllWarcs/archive/*'):
    #         print(it)
    #         with open(it, 'rb') as stream:
    #             for record in ArchiveIterator(stream):
    #                 writter.write_record(record)