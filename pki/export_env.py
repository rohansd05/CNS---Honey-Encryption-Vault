import base64
from pathlib import Path

def get_b64(path):
    try:
        return base64.b64encode(path.read_bytes()).decode('ascii')
    except Exception:
        return ""

def main():
    out_dir = Path(__file__).parent / "out"
    
    print(f"ROOT_CA_CERT_B64={get_b64(out_dir / 'root_ca.crt')}")
    print(f"ISSUING_CA_CERT_B64={get_b64(out_dir / 'issuing_ca.crt')}")
    print(f"ISSUING_CA_KEY_B64={get_b64(out_dir / 'issuing_ca.key')}")
    print(f"HC_CLIENT_CERT_B64={get_b64(out_dir / 'api_client.crt')}")
    print(f"HC_CLIENT_KEY_B64={get_b64(out_dir / 'api_client.key')}")
    print(f"HC_TRUSTED_CA_CERT_B64={get_b64(out_dir / 'root_ca.crt')}")
    print(f"HC_ISSUING_CA_CERT_B64={get_b64(out_dir / 'issuing_ca.crt')}")

if __name__ == "__main__":
    main()
