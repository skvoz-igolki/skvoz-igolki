"""Public product links: actual scripts in isolated file:// and HTTPS deployments."""
from pathlib import Path
import datetime, functools, http.server, ipaddress, os, shutil, ssl, subprocess, tempfile, threading
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
ROOT=Path(__file__).resolve().parents[1]
class QuietFiles(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
with tempfile.TemporaryDirectory(prefix='skvoz-links-',ignore_cleanup_errors=True) as temporary:
    temp=Path(temporary);site=temp/'site';nested=site/'shop'/'sub';nested.mkdir(parents=True)
    for source in ROOT.iterdir():
        if source.is_file() and source.suffix in ['.html','.js','.css','.png','.webp','.ico']:
            shutil.copy2(source,site/source.name);shutil.copy2(source,nested/source.name)
    shutil.copytree(ROOT/'assets',site/'assets')
    shutil.copytree(ROOT/'assets',nested/'assets')
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')]);now=datetime.datetime.now(datetime.timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False).sign(key,hashes.SHA256()))
    (temp/'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (temp/'key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietFiles,directory=str(site)))
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(temp/'cert.pem',temp/'key.pem')
    server.socket=context.wrap_socket(server.socket,server_side=True)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        origin='https://127.0.0.1:'+str(server.server_port)
        for base in [site.as_uri(),origin,origin+'/shop/sub']:
            env=dict(os.environ,SKVOZ_SCENARIO='order_links_scenarios.py',SKVOZ_TEST_BASE=base)
            subprocess.run(['python',str(ROOT/'tests/browser_check.py')],cwd=ROOT,env=env,check=True)
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5)
print('PASS: public config priority, HTTPS auto-detection with subfolder, file:// protection and encoded multi-product Telegram messages; no real Telegram requests.')
