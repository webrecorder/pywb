import yaml
from pywb.cdx.cdxserver import create_cdx_server, CDXServer, RemoteCDXServer
from pywb.cdx.cdxsource import CDXFile, RemoteCDXSource, RedisCDXSource
from pywb.cdx.zipnum import ZipNumCluster

from pywb import get_test_dir

yaml_config = r"""
test_1:
    index_paths:
        # local cdx paths
        - {0}cdx/example.cdx

        # simple remote cdx source, assumes no filtering
        - http://cdxserver.example.com/cdx

        # customized remote cdx server
        - !!python/object:pywb.cdx.cdxsource.RemoteCDXSource {{
            remote_url: 'http://cdxserver.example.com/cdx',
            cookie: custom_token=value,
            remote_processing: true,
        }}

        # example redis cdx source
        - redis://redis.example.com:6379/0

        - {0}zipcdx/zipnum-sample.idx

test_2:
    index_paths: http://cdxserver.example.com/cdx

test_3: http://cdxserver.example.com/cdx

test_4: !!python/object:pywb.cdx.cdxsource.RemoteCDXSource {{
            remote_url: 'http://cdxserver.example.com/cdx',
            cookie: custom_token=value,
            remote_processing: true,
        }}

test_5: {0}cdx/example.cdx

test_6:
    index_paths: invalid://abc


""".format(get_test_dir())

def test_cdxserver_config():
    config = yaml.load(yaml_config)
    cdxserver = create_cdx_server(config.get('test_1'))
    assert(isinstance(cdxserver, CDXServer))
    sources = cdxserver.sources
    assert len(sources) == 5

    assert type(sources[0]) == CDXFile
    assert sources[0].filename.endswith('example.cdx')

    # remote source with no remote processing
    assert type(sources[1]) == RemoteCDXSource
    assert sources[1].remote_url == 'http://cdxserver.example.com/cdx'
    assert sources[1].remote_processing == False

    # remote cdx server with processing
    assert type(sources[2]) == RemoteCDXSource
    assert sources[2].remote_url == 'http://cdxserver.example.com/cdx'
    assert sources[2].remote_processing == True

    # redis source
    assert type(sources[3]) == RedisCDXSource
    assert sources[3].redis_url == 'redis://redis.example.com:6379/0'

    assert type(sources[4]) == ZipNumCluster
    assert sources[4].summary.endswith('zipnum-sample.idx')
    assert sources[4].loc_resolver.loc_filename.endswith('zipnum-sample.loc')


def assert_remote_cdxserver(config_name):
    config = yaml.load(yaml_config)
    cdxserver = create_cdx_server(config.get(config_name))
    assert(isinstance(cdxserver, RemoteCDXServer))

    source = cdxserver.source

    # remote cdx server with remote processing
    assert type(source) == RemoteCDXSource
    assert source.remote_url == 'http://cdxserver.example.com/cdx'
    assert source.remote_processing == True


def test_remote_index_path():
    assert_remote_cdxserver('test_2')

def test_no_index_path_remote():
    assert_remote_cdxserver('test_3')

def test_explicit_remote_source():
    assert_remote_cdxserver('test_4')


def test_single_cdx():
    config = yaml.load(yaml_config)
    cdxserver = create_cdx_server(config.get('test_5'))
    assert(isinstance(cdxserver, CDXServer))
    sources = cdxserver.sources
    assert len(sources) == 1

    assert type(sources[0]) == CDXFile
    assert sources[0].filename.endswith('example.cdx')

def test_invalid_config():
    config = yaml.load(yaml_config)
    cdxserver = create_cdx_server(config.get('test_6'))
    assert(isinstance(cdxserver, CDXServer))
    sources = cdxserver.sources
    assert len(sources) == 0


