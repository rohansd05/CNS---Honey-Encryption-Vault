"""Secure entry sharing service (ECIES + ECDSA sender cert authentication).

Owner: T2 — Rohan. Contract: docs/api-contract.md §5, PROJECT-BRIEF.md §9.
"""

from __future__ import annotations

import base64
import datetime
import json
import logging
import uuid

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.core import Share, User
from app.schemas.shares import (
    OpenShareResponse,
    ShareInboxItem,
    ShareSentItem,
)
from app.services.identity_service import (
    load_private_key,
    pki_configured,
    trusted_ca_pems,
)
from app.services.vault_service import get_or_create_vault
from honeycore.factory import HoneyCore
from honeycore.interfaces import EntryNotFoundError, InvalidSignatureError
from honeycore.pki import PKI
from honeycore.sharing import Sharing

logger = logging.getLogger(__name__)


def _canonical_json(obj: dict) -> bytes:
    """Canonical JSON encoding: sorted keys, compact separators, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _verify_envelope_signature(envelope: dict) -> bool:
    """Verify the envelope's ECDSA signature against the sender certificate public key."""
    try:
        sender_cert_pem = envelope["sender_cert"].encode("ascii")
        sig_b64 = envelope["signature"]
        envelope_without_sig = {k: v for k, v in envelope.items() if k != "signature"}
        envelope_bytes = _canonical_json(envelope_without_sig)

        sender_cert = x509.load_pem_x509_certificate(sender_cert_pem)
        sender_pub = sender_cert.public_key()
        if not isinstance(sender_pub, ec.EllipticCurvePublicKey):
            return False

        der_sig = base64.b64decode(sig_b64)
        sender_pub.verify(der_sig, envelope_bytes, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def create_share(
    db: Session,
    sender: User,
    honeycore: HoneyCore,
    *,
    master_password: str,
    entry_id: str,
    recipient_username: str,
) -> str:
    """Seal a vault entry for recipient_username and store the encrypted Share record."""
    if not pki_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sharing unavailable: PKI not configured",
        )

    if recipient_username == sender.username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot share with yourself",
        )

    recipient = db.scalar(select(User).where(User.username == recipient_username))
    if recipient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if (
        not sender.identity_public_pem
        or not sender.identity_private_wrapped
        or not sender.identity_cert_pem
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has no identity keys",
        )

    if not recipient.identity_public_pem or not recipient.identity_cert_pem:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has no identity keys",
        )

    handle = get_or_create_vault(db, sender, honeycore)
    service: str | None = None
    for e in handle.record.blob.get("entries", []):
        if e.get("id") == entry_id:
            service = e.get("service")
            break

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )

    try:
        seed = handle.vault.export_entry_seed(master_password, entry_id)
    except EntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        ) from exc

    share_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.UTC)
    aad = {
        "sender": sender.username,
        "recipient": recipient.username,
        "service": service,
        "share_id": share_id,
        "created_at": now.isoformat(),
    }

    sharing = Sharing()
    sender_priv = load_private_key(sender)
    recipient_pub = recipient.identity_public_pem.encode("utf-8")
    sender_cert = sender.identity_cert_pem.encode("utf-8")

    envelope = sharing.seal_share(
        seed=seed,
        aad=aad,
        recipient_public_pem=recipient_pub,
        sender_private_pem=sender_priv,
        sender_cert_pem=sender_cert,
    )

    share = Share(
        id=share_id,
        sender_id=sender.id,
        recipient_id=recipient.id,
        service=service,
        envelope=envelope,
        created_at=now,
    )
    db.add(share)
    db.commit()
    db.refresh(share)

    logger.info(
        "Share created successfully: share_id=%s sender=%s recipient=%s",
        share_id,
        sender.username,
        recipient.username,
    )
    return share_id


def get_inbox_shares(db: Session, user: User) -> list[ShareInboxItem]:
    """Retrieve all incoming shares for the current user."""
    stmt = (
        select(Share, User.username)
        .join(User, Share.sender_id == User.id)
        .where(Share.recipient_id == user.id)
        .order_by(Share.created_at.desc())
    )
    rows = db.execute(stmt).all()
    return [
        ShareInboxItem(
            share_id=share.id,
            sender=sender_username,
            service=share.service,
            created_at=share.created_at,
            opened_at=share.opened_at,
        )
        for share, sender_username in rows
    ]


def get_sent_shares(db: Session, user: User) -> list[ShareSentItem]:
    """Retrieve all outgoing shares sent by the current user."""
    stmt = (
        select(Share, User.username)
        .join(User, Share.recipient_id == User.id)
        .where(Share.sender_id == user.id)
        .order_by(Share.created_at.desc())
    )
    rows = db.execute(stmt).all()
    return [
        ShareSentItem(
            share_id=share.id,
            recipient=recipient_username,
            service=share.service,
            created_at=share.created_at,
            opened_at=share.opened_at,
        )
        for share, recipient_username in rows
    ]


def open_share(
    db: Session,
    user: User,
    honeycore: HoneyCore,
    share_id: str,
) -> OpenShareResponse:
    """Verify sender certificate and signature, decrypt share envelope, and decode credential."""
    share = db.get(Share, share_id)
    if share is None or share.recipient_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )

    if share.opened_at is None:
        share.opened_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        db.refresh(share)

    envelope = share.envelope
    sender_cert_pem = envelope.get("sender_cert", "").encode("ascii")
    sender = envelope.get("aad", {}).get("sender", "")
    service = share.service

    pki = PKI()
    cert_subject = ""
    cert_issuer = ""
    try:
        info = pki.describe(sender_cert_pem)
        subject = info.subject_cn
        issuer = info.issuer_cn
        cert_subject = f"CN={subject}" if not subject.startswith("CN=") else subject
        cert_issuer = f"CN={issuer}" if not issuer.startswith("CN=") else issuer
    except Exception:  # noqa: S110
        pass

    try:
        cas = trusted_ca_pems()
    except Exception:
        cas = []

    certificate_valid = True
    try:
        pki.verify_certificate(sender_cert_pem, cas, expected_cn=sender)
    except InvalidSignatureError:
        certificate_valid = False
    except Exception:
        certificate_valid = False

    signature_valid = True
    dec_username = None
    dec_password = None

    if not certificate_valid:
        signature_valid = _verify_envelope_signature(envelope)
    else:
        try:
            sharing = Sharing()
            recipient_priv = load_private_key(user)
            seed, _ = sharing.open_share(envelope, recipient_priv, cas)
            dec_username, dec_password = honeycore.entry_dte.decode(seed)
        except InvalidSignatureError:
            signature_valid = False

    return OpenShareResponse(
        service=service,
        username=dec_username,
        password=dec_password,
        sender=sender,
        signature_valid=signature_valid,
        certificate_valid=certificate_valid,
        certificate_subject=cert_subject,
        certificate_issuer=cert_issuer,
    )


def tamper_share(db: Session, share_id: str) -> bool:
    """Flip one byte in the ciphertext of a stored share envelope (DEMO_MODE only)."""
    settings = get_settings()
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo mode disabled",
        )

    share = db.get(Share, share_id)
    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )

    envelope = dict(share.envelope)
    ciphertext_b64 = envelope.get("ciphertext", "")
    raw_ct = bytearray(base64.b64decode(ciphertext_b64))
    if len(raw_ct) > 0:
        raw_ct[0] ^= 0x01
    envelope["ciphertext"] = base64.b64encode(raw_ct).decode("ascii")
    share.envelope = envelope
    db.commit()
    db.refresh(share)
    return True
