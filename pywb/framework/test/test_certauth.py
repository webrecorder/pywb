import pytest

import os
import shutil

from pywb.framework.certauth import main, CertificateAuthority

TEST_CA_DIR = './pywb/framework/test/pywb_test_ca_certs'
TEST_CA_ROOT = './pywb/framework/test/pywb_test_ca.pem'

def setup_module():
    openssl_support = pytest.importorskip("OpenSSL")
    pass

def test_create_root():
    ret = main([TEST_CA_ROOT, '-n', 'Test Root Cert'])
    assert ret == 0

def test_create_host_cert():
    ret = main(['example.com', '-r', TEST_CA_ROOT, '-d', TEST_CA_DIR])
    assert ret == 0
    certfile = os.path.join(TEST_CA_DIR, 'example.com.pem')
    assert os.path.isfile(certfile)
    #os.remove(certfile)

def test_create_wildcard_host_cert_force_overwrite():
    ret = main(['example.com', '-r', TEST_CA_ROOT, '-d', TEST_CA_DIR, '-w', '-f'])
    assert ret == 0
    certfile = os.path.join(TEST_CA_DIR, 'example.com.pem')
    assert os.path.isfile(certfile)

def test_explicit_wildcard():
    ca = CertificateAuthority(TEST_CA_ROOT, TEST_CA_DIR)
    filename = ca.get_wildcard_cert('test.example.proxy')
    certfile = os.path.join(TEST_CA_DIR, 'example.proxy.pem')
    assert filename == certfile
    assert os.path.isfile(certfile)
    os.remove(certfile)

def test_create_already_exists():
    ret = main(['example.com', '-r', TEST_CA_ROOT, '-d', TEST_CA_DIR, '-w'])
    assert ret == 1
    certfile = os.path.join(TEST_CA_DIR, 'example.com.pem')
    assert os.path.isfile(certfile)
    # remove now
    os.remove(certfile)

def test_create_root_already_exists():
    ret = main([TEST_CA_ROOT])
    # not created, already exists
    assert ret == 1
    # remove now
    os.remove(TEST_CA_ROOT)

def test_delete_files():
    shutil.rmtree(TEST_CA_DIR)
    assert not os.path.isdir(TEST_CA_DIR)
    assert not os.path.isfile(TEST_CA_ROOT)
