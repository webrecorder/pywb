import logging
import os
openssl_avail = False
try:
    from OpenSSL import crypto
    from OpenSSL.SSL import FILETYPE_PEM
    openssl_avail = True
except ImportError:  # pragma: no cover
    pass

import random
from argparse import ArgumentParser


#=================================================================
# Duration of 10 years
CERT_DURATION = 10 * 365 * 24 * 60 * 60

CERTS_DIR = './ca/certs/'

CERT_NAME = 'pywb https proxy replay CA'

CERT_CA_FILE = './ca/pywb-ca.pem'


#=================================================================
class CertificateAuthority(object):
    """
    Utility class for signing individual certificate
    with a root cert.

    Static generate_ca_root() method for creating the root cert

    All certs saved on filesystem. Individual certs are stored
    in specified certs_dir and reused if previously created.
    """

    def __init__(self, ca_file, certs_dir):
        if not ca_file:
            ca_file = CERT_CA_FILE

        if not certs_dir:
            certs_dir = CERTS_DIR

        self.ca_file = ca_file
        self.certs_dir = certs_dir

        # read previously created root cert
        self.cert, self.key = self.read_pem(ca_file)

        if not os.path.exists(certs_dir):
            os.mkdir(certs_dir)

    def get_cert_for_host(self, host, overwrite=False, wildcard=False):
        host_filename = os.path.join(self.certs_dir, host) + '.pem'

        if not overwrite and os.path.exists(host_filename):
            return False, host_filename

        self.generate_host_cert(host, self.cert, self.key, host_filename,
                                wildcard)

        return True, host_filename

    def get_wildcard_cert(self, cert_host):
        host_parts = cert_host.split('.', 1)
        if len(host_parts) == 2 and '.' in host_parts[1]:
            cert_host = host_parts[1]

        created, certfile = self.get_cert_for_host(cert_host,
                                                   wildcard=True)

        return certfile

    def get_root_PKCS12(self):
        p12 = crypto.PKCS12()
        p12.set_certificate(self.cert)
        p12.set_privatekey(self.key)
        return p12.export()

    @staticmethod
    def _make_cert(certname):
        cert = crypto.X509()
        cert.set_version(2)
        cert.set_serial_number(random.randint(0, 2 ** 64 - 1))
        cert.get_subject().CN = certname

        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(CERT_DURATION)
        return cert

    @staticmethod
    def generate_ca_root(ca_file, certname, overwrite=False):
        if not certname:
            certname = CERT_NAME

        if not ca_file:
            ca_file = CERT_CA_FILE

        if not overwrite and os.path.exists(ca_file):
            cert, key = CertificateAuthority.read_pem(ca_file)
            return False, cert, key

        # Generate key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        # Generate cert
        cert = CertificateAuthority._make_cert(certname)

        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.add_extensions([
            crypto.X509Extension(b"basicConstraints",
                                 True,
                                 b"CA:TRUE, pathlen:0"),

            crypto.X509Extension(b"keyUsage",
                                 True,
                                 b"keyCertSign, cRLSign"),

            crypto.X509Extension(b"subjectKeyIdentifier",
                                 False,
                                 b"hash",
                                 subject=cert),
            ])
        cert.sign(key, "sha1")

        # Write cert + key
        CertificateAuthority.write_pem(ca_file, cert, key)
        return True, cert, key

    @staticmethod
    def generate_host_cert(host, root_cert, root_key, host_filename,
                           wildcard=False):
        # Generate key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        # Generate CSR
        req = crypto.X509Req()
        req.get_subject().CN = host
        req.set_pubkey(key)
        req.sign(key, 'sha1')

        # Generate Cert
        cert = CertificateAuthority._make_cert(host)

        cert.set_issuer(root_cert.get_subject())
        cert.set_pubkey(req.get_pubkey())

        if wildcard:
            DNS = 'DNS:'
            alt_hosts = [DNS + host,
                         DNS + '*.' + host]

            alt_hosts = ', '.join(alt_hosts)

            cert.add_extensions([
                crypto.X509Extension('subjectAltName',
                                     False,
                                     alt_hosts)])

        cert.sign(root_key, 'sha1')

        # Write cert + key
        CertificateAuthority.write_pem(host_filename, cert, key)
        return cert, key

    @staticmethod
    def write_pem(filename, cert, key):
        with open(filename, 'wb+') as f:
            f.write(crypto.dump_privatekey(FILETYPE_PEM, key))

            f.write(crypto.dump_certificate(FILETYPE_PEM, cert))

    @staticmethod
    def read_pem(filename):
        with open(filename, 'r') as f:
            cert = crypto.load_certificate(FILETYPE_PEM, f.read())
            f.seek(0)
            key = crypto.load_privatekey(FILETYPE_PEM, f.read())

        return cert, key


#=================================================================
def main(args=None):
    parser = ArgumentParser(description='Cert Auth Cert Maker')

    parser.add_argument('output_pem_file', help='path to cert .pem file')

    parser.add_argument('-r', '--use-root',
                        help=('use specified root cert (.pem file) ' +
                              'to create signed cert'))

    parser.add_argument('-n', '--name', action='store', default=CERT_NAME,
                        help='name for root certificate')

    parser.add_argument('-d', '--certs-dir', default=CERTS_DIR)

    parser.add_argument('-f', '--force', action='store_true')

    parser.add_argument('-w', '--wildcard_cert', action='store_true',
                        help='add wildcard SAN to host: *.<host>, <host>')

    result = parser.parse_args(args=args)

    overwrite = result.force

    # Create a new signed certificate using specified root
    if result.use_root:
        certs_dir = result.certs_dir
        wildcard = result.wildcard_cert
        ca = CertificateAuthority(ca_file=result.use_root,
                                  certs_dir=result.certs_dir)

        created, host_filename = ca.get_cert_for_host(result.output_pem_file,
                                                      overwrite, wildcard)

        if created:
            print ('Created new cert "' + host_filename +
                   '" signed by root cert ' +
                   result.use_root)
            return 0

        else:
            print ('Cert "' + host_filename + '" already exists,' +
                   ' use -f to overwrite')
            return 1

    # Create new root certificate
    else:
        created, c, k = (CertificateAuthority.
                         generate_ca_root(result.output_pem_file,
                                          result.name,
                                          overwrite))

        if created:
            print 'Created new root cert: "' + result.output_pem_file + '"'
            return 0
        else:
            print ('Root cert "' + result.output_pem_file +
                    '" already exists,' + ' use -f to overwrite')
            return 1

if __name__ == "__main__":
    main()
