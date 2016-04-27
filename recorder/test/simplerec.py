from gevent import monkey; monkey.patch_all()

from recorder.recorderapp import RecorderApp
from recorder.redisindexer import WritableRedisIndexer

from recorder.warcwriter import MultiFileWARCWriter
from recorder.filters import SkipDupePolicy

upstream_url = 'http://localhost:8080'

target = './_recordings/'

dedup_index = WritableRedisIndexer(
                redis_url='redis://localhost/2/rec:cdxj',
                file_key_template='rec:warc',
                rel_path_template=target,
                dupe_policy=SkipDupePolicy())

recorder_app = RecorderApp(upstream_url,
                MultiFileWARCWriter(target, dedup_index=dedup_index),
                 accept_colls='live')

application = recorder_app

