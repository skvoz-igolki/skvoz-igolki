"""Integration checks with isolated browser profiles and a temporary HTTPS static server.
No production server, Telegram requests or messages; only existing Python test tools.
"""
from pathlib import Path
import datetime
import functools
import http.server
import ipaddress
import os
import ssl
import subprocess
import tempfile
import threading
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]

class QuietFiles(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path.split('?')[0]=='/product': self.path='/product.html'+('?' + self.path.split('?',1)[1] if '?' in self.path else '')
        super().do_GET()
    def end_headers(self):
        self.send_header('Cache-Control', 'public, max-age=31536000, immutable' if self.path.split('?')[0].endswith(('.js','.css')) else 'no-cache')
        super().end_headers()

with tempfile.TemporaryDirectory(prefix='skvoz-cart-check-',ignore_cleanup_errors=True) as temporary:
    temp = Path(temporary)
    key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1))
        .not_valid_after(now+datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
        .sign(key,hashes.SHA256()))
    cert_path, key_path = temp/'localhost.crt', temp/'localhost.key'
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    server = http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietFiles,directory=os.environ.get('SKVOZ_SITE_ROOT',str(ROOT))))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path,key_path)
    server.socket = context.wrap_socket(server.socket,server_side=True)
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        for label,base in [('file',Path(os.environ.get('SKVOZ_SITE_ROOT',str(ROOT))).as_uri()),('https','https://127.0.0.1:'+str(server.server_port))]:
            profile = temp/('profile-'+label)
            profile.mkdir()
            for mode in ['seed','restore']:
                environment = dict(os.environ,SKVOZ_BROWSER_PROFILE=str(profile),SKVOZ_SCENARIO=os.environ.get('SKVOZ_ORDER_SCENARIO','cart_order_scenarios.py'),SKVOZ_TEST_BASE=base,SKVOZ_ORDER_MODE=mode)
                subprocess.run(['python',str(ROOT/'tests/browser_check.py')],cwd=ROOT,env=environment,check=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
print('PASS: the same persistent-cart and Telegram implementation works through file:// and HTTPS; no real Telegram navigation or messages.')
