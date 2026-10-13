"""Tests for honeycore/sharing.py — ECIES envelope sharing + key wrapping.

Owner: T4 — Parth. Phase 2.
Covers: round-trip; tampered ciphertext/aad/signature/eph_pub; wrong CA;
        CN != aad["sender"]; wrong recipient key; wrap/unwrap round-trip; wrong kek.
"""

from __future__ import annotations

import base64
import copy
import secrets

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from honeycore.interfaces import InvalidSignatureError
from honeycore.pki import PKI, build_issuing_ca, build_root_ca
from honeycore.sharing import Sharing, unwrap_private_key, wrap_private_key

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ca_chain():
    """Build a throwaway Root → Issuing CA chain, returned as PEM bytes."""
    root_cert_pem, root_key_pem = build_root_ca("Test Root CA", 365)
    issuing_cert_pem, issuing_key_pem = build_issuing_ca(
        root_cert_pem, root_key_pem, "Test Issuing CA", 365
    )
    return {
        "root_cert": root_cert_pem,
        "root_key": root_key_pem,
        "issuing_cert": issuing_cert_pem,
        "issuing_key": issuing_key_pem,
        "trusted_cas": [root_cert_pem, issuing_cert_pem],
    }


@pytest.fixture(scope="module")
def alice_identity(ca_chain):
    """Alice's identity keypair + user cert (CN=alice)."""
    pki = PKI()
    sharing = Sharing()
    keys = sharing.generate_identity()
    cert_pem = pki.issue_user_certificate(
        "alice", keys.public_pem, ca_chain["issuing_cert"], ca_chain["issuing_key"], 365
    )
    return {"keys": keys, "cert": cert_pem}


@pytest.fixture(scope="module")
def bob_identity(ca_chain):
    """Bob's identity keypair + user cert (CN=bob)."""
    pki = PKI()
    sharing = Sharing()
    keys = sharing.generate_identity()
    cert_pem = pki.issue_user_certificate(
        "bob", keys.public_pem, ca_chain["issuing_cert"], ca_chain["issuing_key"], 365
    )
    return {"keys": keys, "cert": cert_pem}


@pytest.fixture(scope="module")
def sample_seed():
    return secrets.token_bytes(532)  # ENTRY_SEED_LEN


@pytest.fixture(scope="module")
def sample_aad():
    return {
        "sender": "alice",
        "recipient": "bob",
        "service": "github.com",
        "share_id": "abc123",
        "created_at": "2026-10-05T00:00:00+00:00",
    }


@pytest.fixture(scope="module")
def sealed_envelope(alice_identity, bob_identity, sample_seed, sample_aad):
    """A valid sealed envelope from alice → bob."""
    sharing = Sharing()
    return sharing.seal_share(
        seed=sample_seed,
        aad=sample_aad,
        recipient_public_pem=bob_identity["keys"].public_pem,
        sender_private_pem=alice_identity["keys"].private_pem,
        sender_cert_pem=alice_identity["cert"],
    )


# ---------------------------------------------------------------------------
# 1. Round-trip
# ---------------------------------------------------------------------------


def test_round_trip(sealed_envelope, bob_identity, sample_seed, sample_aad, ca_chain):
    sharing = Sharing()
    seed_out, aad_out = sharing.open_share(
        sealed_envelope,
        bob_identity["keys"].private_pem,
        ca_chain["trusted_cas"],
    )
    assert seed_out == sample_seed
    assert aad_out == sample_aad


# ---------------------------------------------------------------------------
# 2. Tampered ciphertext
# ---------------------------------------------------------------------------


def test_tampered_ciphertext(sealed_envelope, bob_identity, ca_chain):
    bad = copy.deepcopy(sealed_envelope)
    # Flip a byte in the base64-encoded ciphertext
    raw = list(bad["ciphertext"])
    raw[5] = "A" if raw[5] != "A" else "B"
    bad["ciphertext"] = "".join(raw)
    sharing = Sharing()
    with pytest.raises(InvalidSignatureError):
        sharing.open_share(bad, bob_identity["keys"].private_pem, ca_chain["trusted_cas"])


# ---------------------------------------------------------------------------
# 3. Tampered AAD (alters associated_data, breaks GCM auth)
# ---------------------------------------------------------------------------


def test_tampered_aad(sealed_envelope, bob_identity, ca_chain):
    bad = copy.deepcopy(sealed_envelope)
    bad["aad"]["service"] = "evil.com"
    sharing = Sharing()
    with pytest.raises(InvalidSignatureError):
        sharing.open_share(bad, bob_identity["keys"].private_pem, ca_chain["trusted_cas"])


# ---------------------------------------------------------------------------
# 4. Tampered signature
# ---------------------------------------------------------------------------


def test_tampered_signature(sealed_envelope, bob_identity, ca_chain):
    bad = copy.deepcopy(sealed_envelope)
    # Corrupt the base64 signature
    raw_sig = base64.b64decode(bad["signature"])
    raw_sig = bytes([raw_sig[0] ^ 0xFF]) + raw_sig[1:]
    bad["signature"] = base64.b64encode(raw_sig).decode("ascii")
    sharing = Sharing()
    with pytest.raises(InvalidSignatureError):
        sharing.open_share(bad, bob_identity["keys"].private_pem, ca_chain["trusted_cas"])


# ---------------------------------------------------------------------------
# 5. Tampered eph_pub (breaks ECDH → wrong key → GCM fails)
# ---------------------------------------------------------------------------


def test_tampered_eph_pub(sealed_envelope, bob_identity, ca_chain, alice_identity):
    bad = copy.deepcopy(sealed_envelope)
    # Replace eph_pub with a freshly generated public key — ECDH succeeds but wrong key → GCM fails
    other_priv = ec.generate_private_key(ec.SECP256R1())
    other_pub_der = other_priv.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    bad["eph_pub"] = base64.b64encode(other_pub_der).decode("ascii")
    sharing = Sharing()
    with pytest.raises(InvalidSignatureError):
        sharing.open_share(bad, bob_identity["keys"].private_pem, ca_chain["trusted_cas"])


# ---------------------------------------------------------------------------
# 6. Sender cert from a different / untrusted CA
# ---------------------------------------------------------------------------


def test_wrong_ca(sealed_envelope, bob_identity, sample_seed, sample_aad):
    # Build a completely separate CA chain
    wrong_root_cert, wrong_root_key = build_root_ca("Wrong Root CA", 365)
    wrong_issuing_cert, wrong_issuing_key = build_issuing_ca(
        wrong_root_cert, wrong_root_key, "Wrong Issuing CA", 365
    )
    wrong_trusted = [wrong_root_cert, wrong_issuing_cert]

    sharing = Sharing()
    with pytest.raises(InvalidSignatureError):
        sharing.open_share(sealed_envelope, bob_identity["keys"].private_pem, wrong_trusted)


# ---------------------------------------------------------------------------
# 7. CN in cert doesn't match aad["sender"]
# ---------------------------------------------------------------------------


def test_cn_mismatch(bob_identity, ca_chain, sample_seed):
    """Issue a cert to 'mallory' but put 'alice' in aad["sender"]."""
    pki = PKI()
    sharing = Sharing()
    mallory_keys = sharing.generate_identity()
    mallory_cert = pki.issue_user_certificate(
        "mallory",
        mallory_keys.public_pem,
        ca_chain["issuing_cert"],
        ca_chain["issuing_key"],
        365,
    )

    aad = {
        "sender": "alice",  # doesn't match cert CN "mallory"
        "recipient": "bob",
        "service": "github.com",
        "share_id": "xyz",
        "created_at": "2026-10-05T00:00:00+00:00",
    }
    envelope = sharing.seal_share(
        seed=sample_seed,
        aad=aad,
        recipient_public_pem=bob_identity["keys"].public_pem,
        sender_private_pem=mallory_keys.private_pem,
        sender_cert_pem=mallory_cert,
    )

    with pytest.raises(InvalidSignatureError):
        sharing.open_share(envelope, bob_identity["keys"].private_pem, ca_chain["trusted_cas"])


# ---------------------------------------------------------------------------
# 8. Wrong recipient key (correct envelope, different private key)
# ---------------------------------------------------------------------------


def test_wrong_recipient_key(sealed_envelope, ca_chain):
    sharing = Sharing()
    wrong_keys = sharing.generate_identity()
    with pytest.raises(InvalidSignatureError):
        sharing.open_share(sealed_envelope, wrong_keys.private_pem, ca_chain["trusted_cas"])


# ---------------------------------------------------------------------------
# 9. Key wrapping round-trip
# ---------------------------------------------------------------------------


def test_wrap_unwrap_round_trip():
    sharing = Sharing()
    keys = sharing.generate_identity()
    kek = secrets.token_bytes(32)

    wrapped = wrap_private_key(keys.private_pem, kek)
    assert isinstance(wrapped, str)

    recovered = unwrap_private_key(wrapped, kek)
    assert recovered == keys.private_pem


# ---------------------------------------------------------------------------
# 10. Wrong KEK → unwrap fails
# ---------------------------------------------------------------------------


def test_wrap_wrong_kek():
    sharing = Sharing()
    keys = sharing.generate_identity()
    kek = secrets.token_bytes(32)
    wrong_kek = secrets.token_bytes(32)

    wrapped = wrap_private_key(keys.private_pem, kek)
    with pytest.raises(InvalidSignatureError):
        unwrap_private_key(wrapped, wrong_kek)
