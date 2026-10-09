from .base_config_test import BaseConfigTest
from pywb.warcserver.http import DefaultAdapters

from gevent.pywsgi import WSGIServer

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from OpenSSL import crypto

import datetime
import os
import shutil
import tempfile


# ============================================================================
def make_cert(subject, issuer_name, issuer_key, not_before, not_after, is_ca=False, key=None):
    key = key or ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)])

    builder = (x509.CertificateBuilder()
               .subject_name(name)
               .issuer_name(issuer_name or name)
               .public_key(key.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(not_before)
               .not_valid_after(not_after)
               .add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=True))

    if not is_ca:
        builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName(subject)]), critical=False)

    return builder.sign(issuer_key or key, hashes.SHA256()), key


def write_pem(path, cert, key=None):
    with open(path, 'wb') as fh:
        fh.write(cert.public_bytes(serialization.Encoding.PEM))
        if key:
            fh.write(key.private_bytes(serialization.Encoding.PEM,
                                       serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))


def hello_app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'hello']


# ============================================================================
class TestCertReq(BaseConfigTest):
    @classmethod
    def setup_class(cls):
        cls.orig_adapters = (DefaultAdapters.live_adapter, DefaultAdapters.remote_adapter)

        # local test CA, trusted through certificates.ca_cert_dir, signing a valid and an expired cert for localhost
        cls.cert_dir = tempfile.mkdtemp()
        now = datetime.datetime.now(datetime.timezone.utc)
        day = datetime.timedelta(days=1)

        ca_key = ec.generate_private_key(ec.SECP256R1())
        ca_cert, _ = make_cert('pywb test ca', None, ca_key, now - day, now + day, is_ca=True, key=ca_key)

        # ca_cert_dir is looked up by subject name hash, as created by c_rehash
        ca_hash = '%08x' % crypto.X509.from_cryptography(ca_cert).subject_name_hash()
        ca_dir = os.path.join(cls.cert_dir, 'ca')
        os.mkdir(ca_dir)
        write_pem(os.path.join(ca_dir, ca_hash + '.0'), ca_cert)

        cls.servers = {}
        for name, not_after in (('good', now + day), ('expired', now - day)):
            cert, key = make_cert('localhost', ca_cert.subject, ca_key, now - 2 * day, not_after)
            path = os.path.join(cls.cert_dir, name + '.pem')
            write_pem(path, cert, key)

            server = WSGIServer(('localhost', 0), hello_app, certfile=path, keyfile=path)
            server.start()
            cls.servers[name] = server

        super(TestCertReq, cls).setup_class('config_test_cert_req.yaml',
                                            custom_config={'certificates': {'cert_reqs': 'CERT_REQUIRED',
                                                                            'ca_cert_dir': ca_dir}})

    @classmethod
    def teardown_class(cls):
        for server in cls.servers.values():
            server.stop()

        shutil.rmtree(cls.cert_dir)
        DefaultAdapters.live_adapter, DefaultAdapters.remote_adapter = cls.orig_adapters
        super(TestCertReq, cls).teardown_class()

    def get_url(self, name):
        return 'https://localhost:{0}/'.format(self.servers[name].server_port)

    def test_expired_cert(self):
        resp = self.testapp.get('/live/mp_/' + self.get_url('expired'), status='*')

        assert resp.status_int == 400

    def test_good_cert(self):
        resp = self.testapp.get('/live/mp_/' + self.get_url('good'), status='*')

        assert resp.status_int == 200
        assert resp.text == 'hello'
