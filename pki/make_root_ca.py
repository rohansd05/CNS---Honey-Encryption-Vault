import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from honeycore.pki import build_root_ca

def main():
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)
    
    cert_pem, key_pem = build_root_ca(cn="HoneyVault Root CA", days=3650)
    
    cert_path = out_dir / "root_ca.crt"
    key_path = out_dir / "root_ca.key"
    
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)
    
    if os.name != 'nt':
        key_path.chmod(0o600)

if __name__ == "__main__":
    main()
