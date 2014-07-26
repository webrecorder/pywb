import logging
import os
import OpenSSL
import random


class CertificateAuthority(object):
    logger = logging.getLogger('pywb.CertificateAuthority')

    def __init__(self, ca_file='pywb-ca.pem',
                       certs_dir='./pywb-ca',
                       certname='pywb CA'):

        self.ca_file = ca_file
        self.certs_dir = certs_dir
        self.certname = certname

        if not os.path.exists(ca_file):
            self._generate_ca()
        else:
            self._read_ca(ca_file)

        if not os.path.exists(certs_dir):
            self.logger.info("directory for generated certs {} doesn't exist, creating it".format(certs_dir))
            os.mkdir(certs_dir)


    def _generate_ca(self):
        # Generate key
        self.key = OpenSSL.crypto.PKey()
        self.key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)

        # Generate certificate
        self.cert = OpenSSL.crypto.X509()
        self.cert.set_version(3)
        # avoid sec_error_reused_issuer_and_serial
        self.cert.set_serial_number(random.randint(0,2**64-1))
        self.cert.get_subject().CN = self.certname
        self.cert.gmtime_adj_notBefore(0)                # now
        self.cert.gmtime_adj_notAfter(100*365*24*60*60)  # 100 yrs in future
        self.cert.set_issuer(self.cert.get_subject())
        self.cert.set_pubkey(self.key)
        self.cert.add_extensions([
            OpenSSL.crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE, pathlen:0"),
            OpenSSL.crypto.X509Extension(b"keyUsage", True, b"keyCertSign, cRLSign"),
            OpenSSL.crypto.X509Extension(b"subjectKeyIdentifier", False, b"hash", subject=self.cert),
            ])
        self.cert.sign(self.key, "sha1")

        with open(self.ca_file, 'wb+') as f:
            f.write(OpenSSL.crypto.dump_privatekey(OpenSSL.SSL.FILETYPE_PEM, self.key))
            f.write(OpenSSL.crypto.dump_certificate(OpenSSL.SSL.FILETYPE_PEM, self.cert))

        self.logger.info('generated CA key+cert and wrote to {}'.format(self.ca_file))


    def _read_ca(self, filename):
        self.cert = OpenSSL.crypto.load_certificate(OpenSSL.SSL.FILETYPE_PEM, open(filename).read())
        self.key = OpenSSL.crypto.load_privatekey(OpenSSL.SSL.FILETYPE_PEM, open(filename).read())
        self.logger.info('read CA key+cert from {}'.format(self.ca_file))

    def __getitem__(self, cn):
        cnp = os.path.sep.join([self.certs_dir, '%s.pem' % cn])
        if not os.path.exists(cnp):
            # create certificate
            key = OpenSSL.crypto.PKey()
            key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)

            # Generate CSR
            req = OpenSSL.crypto.X509Req()
            req.get_subject().CN = cn
            req.set_pubkey(key)
            req.sign(key, 'sha1')

            # Sign CSR
            cert = OpenSSL.crypto.X509()
            cert.set_subject(req.get_subject())
            cert.set_serial_number(random.randint(0,2**64-1))
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(10*365*24*60*60)
            cert.set_issuer(self.cert.get_subject())
            cert.set_pubkey(req.get_pubkey())
            cert.sign(self.key, 'sha1')

            with open(cnp, 'wb+') as f:
                f.write(OpenSSL.crypto.dump_privatekey(OpenSSL.SSL.FILETYPE_PEM, key))
                f.write(OpenSSL.crypto.dump_certificate(OpenSSL.SSL.FILETYPE_PEM, cert))

            self.logger.info('wrote generated key+cert to {}'.format(cnp))

        return cnp
