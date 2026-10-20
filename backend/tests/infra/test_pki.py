import pytest
from cryptography.hazmat.primitives import serialization

from honeycore.interfaces import InvalidSignatureError
from honeycore.pki import PKI, build_issuing_ca, build_root_ca, generate_ec_key, issue_leaf


def test_pki():
    pki = PKI()

    root_cert_pem, root_key_pem = build_root_ca("Test Root", 365)
    issuing_cert_pem, issuing_key_pem = build_issuing_ca(
        root_cert_pem, root_key_pem, "Test Issuing", 365
    )

    user_priv = generate_ec_key()
    user_pub_pem = user_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    user_cert_pem = pki.issue_user_certificate(
        "alice", user_pub_pem, issuing_cert_pem, issuing_key_pem, 365
    )

    # 1. Valid chain
    cert_info = pki.verify_certificate(
        user_cert_pem, [root_cert_pem, issuing_cert_pem], expected_cn="alice"
    )
    assert cert_info.subject_cn == "alice"
    assert cert_info.issuer_cn == "Test Issuing"

    # 2. Describe fields
    info = pki.describe(user_cert_pem)
    assert info.subject_cn == "alice"
    assert info.issuer_cn == "Test Issuing"
    assert info.serial > 0
    assert info.not_before
    assert info.not_after
    assert len(info.fingerprint_sha256) == 64

    # 3. Cert from an entirely different CA tree → chain building fails
    other_root_cert, other_root_key = build_root_ca("Other Root", 365)
    other_issuing_cert, other_issuing_key = build_issuing_ca(
        other_root_cert, other_root_key, "Other Issuing", 365
    )
    other_cert_pem = pki.issue_user_certificate(
        "alice", user_pub_pem, other_issuing_cert, other_issuing_key, 365
    )
    with pytest.raises(InvalidSignatureError):
        pki.verify_certificate(other_cert_pem, [root_cert_pem, issuing_cert_pem])

    # 4. Wrong root
    wrong_root_cert, wrong_root_key = build_root_ca("Wrong Root", 365)
    with pytest.raises(InvalidSignatureError, match="Chain building failed"):
        pki.verify_certificate(user_cert_pem, [wrong_root_cert, issuing_cert_pem])

    # 5. Expired leaf (issued with past validity)
    expired_cert_pem = issue_leaf(issuing_cert_pem, issuing_key_pem, "bob", user_pub_pem, -10)
    with pytest.raises(InvalidSignatureError, match="expired"):
        pki.verify_certificate(expired_cert_pem, [root_cert_pem, issuing_cert_pem])

    # 6. CN mismatch
    with pytest.raises(InvalidSignatureError, match="CN mismatch"):
        pki.verify_certificate(user_cert_pem, [root_cert_pem, issuing_cert_pem], expected_cn="bob")

    # 7. require_client_auth on user vs api-client certs
    with pytest.raises(InvalidSignatureError, match="Client auth EKU required"):
        pki.verify_certificate(
            user_cert_pem, [root_cert_pem, issuing_cert_pem], require_client_auth=True
        )

    api_cert_pem = issue_leaf(
        issuing_cert_pem, issuing_key_pem, "api", user_pub_pem, 365, eku_client_auth=True
    )
    pki.verify_certificate(
        api_cert_pem, [root_cert_pem, issuing_cert_pem], require_client_auth=True
    )


def test_pki_rejects_untrusted_root_terminus():
    pki = PKI()
    root_cert_pem, root_key_pem = build_root_ca("Test Root", 365)
    issuing_cert_pem, issuing_key_pem = build_issuing_ca(
        root_cert_pem, root_key_pem, "Test Issuing", 365
    )

    user_priv = generate_ec_key()
    user_pub_pem = user_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    user_cert_pem = pki.issue_user_certificate(
        "alice", user_pub_pem, issuing_cert_pem, issuing_key_pem, 365
    )

    # 1. Untrusted self-signed root CA used directly as issuer
    untrusted_root_pem, untrusted_root_key_pem = build_root_ca("Untrusted Root", 365)
    untrusted_user_pem = pki.issue_user_certificate(
        "alice", user_pub_pem, untrusted_root_pem, untrusted_root_key_pem, 365
    )
    with pytest.raises(InvalidSignatureError, match="Chain building failed"):
        pki.verify_certificate(untrusted_user_pem, [root_cert_pem, issuing_cert_pem])

    # 2. Untrusted self-signed CA presented directly as leaf cert
    with pytest.raises(InvalidSignatureError):
        pki.verify_certificate(untrusted_root_pem, [root_cert_pem, issuing_cert_pem])

    # 3. Trusted root CA presented as leaf cert
    with pytest.raises(InvalidSignatureError, match="CA"):
        pki.verify_certificate(root_cert_pem, [root_cert_pem, issuing_cert_pem])

    # 4. Chain missing trusted Root CA (only intermediate supplied)
    with pytest.raises(InvalidSignatureError, match="Chain building failed"):
        pki.verify_certificate(user_cert_pem, [issuing_cert_pem])


def test_pki_rejects_issuer_without_key_cert_sign():
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.x509.oid import NameOID

    pki = PKI()
    root_cert_pem, root_key_pem = build_root_ca("Test Root", 365)
    root_cert = x509.load_pem_x509_certificate(root_cert_pem)
    root_key = serialization.load_pem_private_key(root_key_pem, password=None)

    user_priv = generate_ec_key()
    user_pub_pem = user_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Intermediate CA with BasicConstraints(ca=True) but KeyUsage(key_cert_sign=False)
    bad_ca_key = generate_ec_key()
    bad_ca_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Bad CA No Sign")]))
        .issuer_name(root_cert.subject)
        .public_key(bad_ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )
    bad_ca_pem = bad_ca_cert.public_bytes(serialization.Encoding.PEM)
    bad_ca_key_pem = bad_ca_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    user_cert_bad_ca = pki.issue_user_certificate(
        "alice", user_pub_pem, bad_ca_pem, bad_ca_key_pem, 365
    )
    with pytest.raises(InvalidSignatureError, match="keyCertSign"):
        pki.verify_certificate(user_cert_bad_ca, [root_cert_pem, bad_ca_pem])

    # Intermediate CA with BasicConstraints(ca=True) but missing KeyUsage extension entirely
    no_ku_key = generate_ec_key()
    no_ku_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Bad CA No KU")]))
        .issuer_name(root_cert.subject)
        .public_key(no_ku_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(root_key, hashes.SHA256())
    )
    no_ku_pem = no_ku_cert.public_bytes(serialization.Encoding.PEM)
    no_ku_key_pem = no_ku_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    user_cert_no_ku = pki.issue_user_certificate(
        "alice", user_pub_pem, no_ku_pem, no_ku_key_pem, 365
    )
    with pytest.raises(InvalidSignatureError, match="KeyUsage"):
        pki.verify_certificate(user_cert_no_ku, [root_cert_pem, no_ku_pem])


def test_pki_rejects_path_length_violations():
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.x509.oid import NameOID

    pki = PKI()
    user_priv = generate_ec_key()
    user_pub_pem = user_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # 1. Intermediate CA with path_length=0 issues another intermediate CA
    root_cert_pem, root_key_pem = build_root_ca("Test Root", 365)
    issuing1_pem, issuing1_key_pem = build_issuing_ca(
        root_cert_pem, root_key_pem, "Test Issuing 1", 365
    )
    issuing2_pem, issuing2_key_pem = build_issuing_ca(
        issuing1_pem, issuing1_key_pem, "Test Issuing 2", 365
    )
    user_cert_from_issuing2 = pki.issue_user_certificate(
        "alice", user_pub_pem, issuing2_pem, issuing2_key_pem, 365
    )
    with pytest.raises(InvalidSignatureError, match="Path length constraint violated"):
        pki.verify_certificate(user_cert_from_issuing2, [root_cert_pem, issuing1_pem, issuing2_pem])

    # 2. Root CA with path_length=0 issues an intermediate CA
    priv = generate_ec_key()
    root0_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Root PathLen 0")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Root PathLen 0")]))
        .public_key(priv.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(priv, hashes.SHA256())
    )
    root0_pem = root0_cert.public_bytes(serialization.Encoding.PEM)
    root0_key_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    issuing_under_root0_pem, issuing_under_root0_key = build_issuing_ca(
        root0_pem, root0_key_pem, "Issuing Under Root0", 365
    )
    user_cert_root0 = pki.issue_user_certificate(
        "alice", user_pub_pem, issuing_under_root0_pem, issuing_under_root0_key, 365
    )
    with pytest.raises(InvalidSignatureError, match="Path length constraint violated"):
        pki.verify_certificate(user_cert_root0, [root0_pem, issuing_under_root0_pem])


def test_pki_rejects_unintended_trusted_root_terminus():
    pki = PKI()
    root_cert_pem, root_key_pem = build_root_ca("Test Root", 365)
    issuing_cert_pem, issuing_key_pem = build_issuing_ca(
        root_cert_pem, root_key_pem, "Test Issuing", 365
    )

    other_root_pem, other_root_key = build_root_ca("Other Root", 365)

    user_priv = generate_ec_key()
    user_pub_pem = user_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    other_user_pem = pki.issue_user_certificate(
        "alice", user_pub_pem, other_root_pem, other_root_key, 365
    )

    # 1. Multi-root trust list: leaf chains to Other Root,
    # but caller specifies expected_root_cn="Test Root"
    with pytest.raises(InvalidSignatureError, match="Root CA CN mismatch"):
        pki.verify_certificate(
            other_user_pem,
            [root_cert_pem, other_root_pem, issuing_cert_pem],
            expected_root_cn="Test Root",
        )

    # 2. Correct root passes expected_root_cn
    valid_user_pem = pki.issue_user_certificate(
        "alice", user_pub_pem, issuing_cert_pem, issuing_key_pem, 365
    )
    info = pki.verify_certificate(
        valid_user_pem,
        [root_cert_pem, other_root_pem, issuing_cert_pem],
        expected_root_cn="Test Root",
    )
    assert info.subject_cn == "alice"

    # 3. Empty trust list is rejected
    with pytest.raises(InvalidSignatureError, match="Trust store is empty"):
        pki.verify_certificate(valid_user_pem, [])

    # 4. Multi-root trust list where expected_root_cn is omitted:
    # chain terminating at secondary/unintended root in the trust list is rejected
    with pytest.raises(InvalidSignatureError, match="unintended root CA"):
        pki.verify_certificate(
            other_user_pem,
            [root_cert_pem, other_root_pem, issuing_cert_pem],
        )

    # Primary intended root in the same multi-root trust list passes without expected_root_cn
    info_primary = pki.verify_certificate(
        valid_user_pem,
        [root_cert_pem, other_root_pem, issuing_cert_pem],
    )
    assert info_primary.subject_cn == "alice"
