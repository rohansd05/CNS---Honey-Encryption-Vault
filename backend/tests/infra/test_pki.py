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
