import uuid
import os

import boto3
from pathlib import Path
import pytest

from pywb.recorder.s3uploader import (
    s3_upload_file, validate_warc_filename, validate_index_filename,
    WARCValidationError, BucketValidationError)


TEST_BUCKET = 'pywbtest'


def get_test_file(prefix):
    filepath = f'/{prefix}/{"".join(str(uuid.uuid4()).split("-"))}.txt'
    Path(filepath).touch()
    return filepath


def test_s3_upload_file():
    prefix = 'tmp'
    filepath = get_test_file(prefix)
    assert s3_upload_file(filepath, TEST_BUCKET)

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(TEST_BUCKET)
    filename = filepath.lstrip('/')
    assert filename in list(map(lambda x: x.key, bucket.objects.filter(Prefix=prefix)))

    s3.Object(TEST_BUCKET, filename).delete()


def test_s3_upload_file_with_env_var():
    prefix = 'tmp'
    filepath = get_test_file(prefix)

    os.environ['AWS_S3_BUCKET'] = TEST_BUCKET
    assert s3_upload_file(filepath)

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(TEST_BUCKET)
    filename = filepath.lstrip('/')
    assert filename in list(map(lambda x: x.key, bucket.objects.filter(Prefix=prefix)))

    s3.Object(TEST_BUCKET, filename).delete()
    os.environ.pop('AWS_S3_BUCKET')


def test_s3_upload_file_with_no_bucket():
    filepath = get_test_file('tmp')
    with pytest.raises(BucketValidationError):
        s3_upload_file(filepath)



@pytest.mark.parametrize('filepath,exc', [
    ['collections/TESTcoll/archive/rec-20201110135059218436-user.warc.gz', None],
    ['collections/TESTcoll/archive/anything.warc.gz', None],
    ['collections/TESTcoll/archive/anything.gz', WARCValidationError],
    ['collections/TESTcoll/archive/anything.warc.zip', WARCValidationError],
    ['collections/invalid&/archive/rec-20201110135059218436-user.warc.gz', WARCValidationError],
    ['notacollection/test/archive/rec-20201110135059218436-user.warc.gz', WARCValidationError],
    ['collection/test/notanarchive/rec-20201110135059218436-user.warc.gz', WARCValidationError],
])
def test_validate_warc_filename(filepath, exc):
    if exc:
        with pytest.raises(exc):
            validate_warc_filename(filepath)
    else:
        validate_warc_filename(filepath)


@pytest.mark.parametrize('filepath,exc', [
    ['collections/TESTcoll/indexes/index.cdxj', None],
    ['collections/TESTcoll/indexes/anything.cdxj', None],
    ['collections/TESTcoll/indexes/anything.index', WARCValidationError],
    ['collections/TESTcoll/indexes/anything.', WARCValidationError],
    ['collections/TEST*coll/indexes/anything.cdxj', WARCValidationError],
    ['collections/TESTcoll/indexes/anything', WARCValidationError],
    ['collections/TESTcoll/notindexes/anything.cdxj', WARCValidationError],
])
def test_validate_index_filename(filepath, exc):
    if exc:
        with pytest.raises(exc):
            validate_index_filename(filepath)
    else:
        validate_index_filename(filepath)