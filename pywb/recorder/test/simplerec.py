from gevent import monkey; monkey.patch_all()

from recorder.recorderapp import RecorderApp
from recorder.redisindexer import WritableRedisIndexer

from recorder.warcwriter import MultiFileWARCWriter
from recorder.filters import SkipDupePolicy

import atexit
import tempfile
import redis

upstream_url = 'http://localhost:8080'

target = tempfile.mkdtemp(prefix='tmprec') + '/'

print('Recording to ' + target)

def rm_target():
    print('Removing ' + target)
    shutil.rmtree(target)

atexit.register(rm_target)

local_r = redis.StrictRedis.from_url('redis://localhost/2')
local_r.delete('rec:cdxj')
local_r.delete('rec:warc')

#target = './_recordings/'

dedup_index = WritableRedisIndexer(
                redis_url='redis://localhost/2/rec:cdxj',
                file_key_template='rec:warc',
                rel_path_template=target,
                dupe_policy=SkipDupePolicy())

recorder_app = RecorderApp(upstream_url,
                MultiFileWARCWriter(target, dedup_index=dedup_index),
                 accept_colls='live')

application = recorder_app

