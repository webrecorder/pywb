import boto3
from botocore.exceptions import ClientError
import logging
import os
import re


s3log = logging.getLogger('s3log')


class WARCValidationError(Exception):
    pass


class BucketValidationError(Exception):
    pass


def s3_upload_file(filename: str, bucket: str=None, object_name=None):
    """Upload a file to an S3 bucket

    :param filename: Full path to file to upload
    :param bucket: Bucket to upload to. If not passed, expect to
        find this in the AWS_S3_BUCKET environment variable
    :return: True if file was uploaded, else False
    """
    # Clean up bucket and filenames
    bucket = bucket or os.environ.get('AWS_S3_BUCKET')
    if not bucket:
        raise BucketValidationError('No S3 bucket provided')

    bucket = bucket.lstrip('s3://')
    obj_name = object_name or filename.lstrip('/')

    s3client = boto3.client('s3')
    try:
        s3log.info(f'Uploading {filename} to {bucket}')
        response = s3client.upload_file(filename, bucket, obj_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def validate_warc_filename(filename: str):
    warc_pattern = r'collections\/[\w\-]+\/archive\/[\w\-.]+\.warc\.gz'
    if not re.match(warc_pattern, filename):
        raise WARCValidationError(f'File {filename} is not a valid warc path')


def validate_index_filename(filename: str):
    index_pattern = r'collections\/[\w\-]+\/indexes\/[\w\-]+\.cdxj'
    if not re.match(index_pattern, filename):
        raise WARCValidationError(f'File {filename} is not a valid index path')


def s3_upload_warc(filename: str, bucket: str=None):
    validate_warc_filename(filename)
    return s3_upload_file(filename, bucket)


def s3_upload_index(filename: str, bucket: str=None):
    validate_index_filename(filename)
    return s3_upload_file(filename, bucket)
