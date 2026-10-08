import os
import requests
import urllib3
import datetime
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def generate_throwaway_cert():
    # Generate CA
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"Throwaway CA")])
    ca_cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
        ca_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.utcnow()).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=1)).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True).sign(ca_key, hashes.SHA256())

    # Generate Client Cert
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"throwaway-user")])
    client_cert = x509.CertificateBuilder().subject_name(client_subject).issuer_name(issuer).public_key(
        client_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.utcnow()).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=1)).add_extension(
        x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False).sign(ca_key, hashes.SHA256())

    with open("throwaway-client.key", "wb") as f:
        f.write(client_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    with open("throwaway-client.crt", "wb") as f:
        f.write(client_cert.public_bytes(serialization.Encoding.PEM))

def cleanup_throwaway_cert():
    if os.path.exists("throwaway-client.key"):
        os.remove("throwaway-client.key")
    if os.path.exists("throwaway-client.crt"):
        os.remove("throwaway-client.crt")

def run_tests():
    url = "https://localhost:8001/hc/health"
    ca_cert_path = "../pki/out/service-ca.crt"
    api_cert = ("../pki/out/api-client.crt", "../pki/out/api-client.key")
    
    results = []

    # Test 1: No client cert
    try:
        res = requests.get(url, verify=ca_cert_path, timeout=5)
        results.append(("1. No client cert", "FAIL (expected failure, got {} {})".format(res.status_code, res.text)))
    except requests.exceptions.SSLError:
        results.append(("1. No client cert", "PASS"))
    except Exception as e:
        results.append(("1. No client cert", f"FAIL (unexpected error: {e})"))

    # Test 2: API client cert
    try:
        res = requests.get(url, cert=api_cert, verify=ca_cert_path, timeout=5)
        if res.status_code == 200:
            results.append(("2. With API client cert", "PASS"))
        else:
            results.append(("2. With API client cert", f"FAIL (got status {res.status_code})"))
    except Exception as e:
        results.append(("2. With API client cert", f"FAIL (error: {e})"))

    # Test 3: Throwaway cert
    generate_throwaway_cert()
    try:
        res = requests.get(url, cert=("throwaway-client.crt", "throwaway-client.key"), verify=ca_cert_path, timeout=5)
        results.append(("3. With throwaway cert", f"FAIL (expected failure, got {res.status_code})"))
    except requests.exceptions.SSLError:
        results.append(("3. With throwaway cert", "PASS"))
    except Exception as e:
        results.append(("3. With throwaway cert", f"FAIL (unexpected error: {e})"))
    finally:
        cleanup_throwaway_cert()

    print(f"{'TEST':<30} | {'RESULT'}")
    print("-" * 50)
    for test, result in results:
        print(f"{test:<30} | {result}")

if __name__ == "__main__":
    run_tests()
