import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from honeycore.pki import issue_leaf, generate_ec_key
from cryptography.hazmat.primitives import serialization

def main():
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)
    
    issuing_cert = (out_dir / "issuing_ca.crt").read_bytes()
    issuing_key = (out_dir / "issuing_ca.key").read_bytes()
    
    # 1. honeychecker-server
    hc_priv = generate_ec_key()
    hc_pub = hc_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    hc_cert = issue_leaf(
        issuer_cert_pem=issuing_cert,
        issuer_key_pem=issuing_key,
        cn="honeychecker-server",
        public_pem=hc_pub,
        days=365,
        san_dns=["localhost", "honeychecker"],
        san_ip=["127.0.0.1"],
        eku_server_auth=True
    )
    (out_dir / "honeychecker.crt").write_bytes(hc_cert)
    hc_key_path = out_dir / "honeychecker.key"
    hc_key_path.write_bytes(hc_priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))
    if os.name != 'nt':
        hc_key_path.chmod(0o600)
        
    # 2. api-client
    api_priv = generate_ec_key()
    api_pub = api_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    api_cert = issue_leaf(
        issuer_cert_pem=issuing_cert,
        issuer_key_pem=issuing_key,
        cn="honeyvault-api",
        public_pem=api_pub,
        days=365,
        eku_client_auth=True
    )
    (out_dir / "api_client.crt").write_bytes(api_cert)
    api_key_path = out_dir / "api_client.key"
    api_key_path.write_bytes(api_priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))
    if os.name != 'nt':
        api_key_path.chmod(0o600)

if __name__ == "__main__":
    main()
