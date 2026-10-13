"""Security regression suite for AGENTS.md §1 invariants. Owner: T1 — Dhruv.

Runs the real honey vault (Argon2id ``demo`` profile + AES-256-CTR) with the stub entry DTE.
If any test here fails, the honey vault has (re)gained a password oracle — do not "fix" the
test, fix the code.
"""

from __future__ import annotations

import base64
import re
import secrets
import string
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from honeycore.interfaces import ENTRY_SEED_LEN, MAX_FIELD_LEN, PRINTABLE_MAX, PRINTABLE_MIN, Entry
from honeycore.sigil import EMOJI64, PALETTE16
from honeycore.stubs import StubEntryDTE
from honeycore.vault import HoneyVault

BACKEND = Path(__file__).resolve().parents[2]
HONEYCORE = BACKEND / "honeycore"

MASTER = "correct-horse-master-9"
Vault = HoneyVault.bind(StubEntryDTE())
ENTRIES = [
    Entry("github.com", "alice@gmail.com", "monkey123!"),
    Entry("mail.google.com", "alice", "P@ssw0rd"),
    Entry("bank.example", "alice_1990", "correct horse battery"),
]

# Blob field names that would suggest an authenticator / verifier (an offline oracle).
FORBIDDEN_NAME_PARTS = ("mac", "tag", "hash", "verifier", "check")
# ``kdf.hash_len`` is the frozen v1 Argon2 OUTPUT LENGTH parameter (§7.8), not a stored hash.
ALLOWED_FIELD_PATHS = {("kdf", "hash_len")}


@pytest.fixture(scope="module")
def vault() -> HoneyVault:
    v = Vault.new("demo")
    for e in ENTRIES:
        v.add_entry(MASTER, e)
    return v


def _printable_field(value: str) -> bool:
    return 1 <= len(value) <= MAX_FIELD_LEN and all(
        PRINTABLE_MIN <= ord(c) <= PRINTABLE_MAX for c in value
    )


def _random_passwords(n: int) -> list[str]:
    """Varied candidate passwords: ASCII, whitespace, control chars, any Unicode, very long."""
    fixed = [
        "",
        " ",
        "\t\n",
        "\x00",
        "\x00" * 64,
        MASTER + " ",
        " " + MASTER,
        MASTER.upper(),
        MASTER[:-1],
        "\ud800",
        "a\udfffb",
        "🍯🐝" * 100,
        "x" * 100_000,
        "pässwörd",
        "密码密码",
        "‮evil",
    ]
    out = list(fixed)
    ascii_alphabet = string.printable
    while len(out) < n:
        kind = len(out) % 5
        if kind == 0:  # printable ASCII
            size = 1 + secrets.randbelow(40)
            out.append("".join(secrets.choice(ascii_alphabet) for _ in range(size)))
        elif kind == 1:  # any code point, including surrogates and non-characters
            size = 1 + secrets.randbelow(24)
            out.append("".join(chr(secrets.randbelow(0x110000)) for _ in range(size)))
        elif kind == 2:  # whitespace-only
            out.append("".join(secrets.choice(" \t\r\n 　") for _ in range(8)))
        elif kind == 3:  # long
            out.append(secrets.token_urlsafe(1 + secrets.randbelow(4000)))
        else:  # near-misses of the real password
            i = secrets.randbelow(len(MASTER))
            out.append(MASTER[:i] + secrets.choice(string.ascii_letters) + MASTER[i + 1 :])
        if out[-1] == MASTER:
            out.pop()
    return out[:n]


def _walk(obj: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[tuple[Any, ...], Any]]:
    """Yield ``(path, value)`` for every node; dict keys appear as the last path element."""
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, (*path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, (*path, i))


# --- (a) unlock never raises -------------------------------------------------------------


def test_unlock_never_raises_for_500_passwords(vault: HoneyVault) -> None:
    passwords = _random_passwords(500)
    assert len(passwords) == 500
    for pw in passwords:
        result = vault.unlock(pw)
        assert len(result.entries) == len(ENTRIES)
        assert [e.service for e in result.entries] == [e.service for e in ENTRIES]
        for e in result.entries:
            assert _printable_field(e.username) and _printable_field(e.password)
        assert len(result.sigil.emojis) == 3
        assert all(emoji in EMOJI64 for emoji in result.sigil.emojis)
        assert result.sigil.color in PALETTE16


def test_unlock_does_not_mutate_the_blob(vault: HoneyVault) -> None:
    before = vault.to_dict()
    vault.unlock(MASTER)
    vault.unlock("wrong")
    assert vault.to_dict() == before


def test_export_entry_seed_never_raises_for_wrong_password(vault: HoneyVault) -> None:
    entry_id = vault.to_dict()["entries"][0]["id"]
    for pw in _random_passwords(30):
        assert len(vault.export_entry_seed(pw, entry_id)) == ENTRY_SEED_LEN


# --- (b) fixed-length ciphertext, no tag -------------------------------------------------


def test_ciphertext_is_exactly_entry_seed_len_without_tag(vault: HoneyVault) -> None:
    blob = vault.to_dict()
    assert blob["entries"]
    for e in blob["entries"]:
        assert len(base64.b64decode(e["ciphertext"], validate=True)) == ENTRY_SEED_LEN
        assert "tag" not in e
        assert set(e) == {"id", "service", "nonce", "ciphertext", "created_at", "updated_at"}


# --- (c) no authenticator-like field names -----------------------------------------------


def test_blob_has_no_mac_tag_hash_verifier_or_check_fields(vault: HoneyVault) -> None:
    blob = vault.to_dict()
    names = [path for path, _ in _walk(blob) if path and isinstance(path[-1], str)]
    assert names  # sanity: the walk saw the blob's keys
    for path in names:
        if path in ALLOWED_FIELD_PATHS:
            continue
        name = path[-1].lower()
        for part in FORBIDDEN_NAME_PARTS:
            assert part not in name, f"suspicious blob field {'.'.join(map(str, path))!r}"


def test_allowlist_is_only_the_kdf_output_length(vault: HoneyVault) -> None:
    blob = vault.to_dict()
    assert isinstance(blob["kdf"]["hash_len"], int)
    assert blob["kdf"]["hash_len"] == 32


# --- (d) no authenticated-encryption code in the honey path ------------------------------

FORBIDDEN_SOURCE = ("AESGCM", "hmac.compare", "InvalidTag")


@pytest.mark.parametrize("module", ["vault.py", "cipher.py", "kdf.py", "sigil.py"])
def test_honey_path_source_has_no_aead_or_verification(module: str) -> None:
    source = (HONEYCORE / module).read_text(encoding="utf-8")
    for token in FORBIDDEN_SOURCE:
        assert token not in source, f"{module} references {token}"


def test_no_random_module_in_honeycore_or_app() -> None:
    # AGENTS.md §1.5: only ``secrets`` / ``os.urandom``.
    pattern = re.compile(r"^\s*(import\s+random\b|from\s+random\s+import)", re.MULTILINE)
    offenders = [
        str(p.relative_to(BACKEND))
        for root in ("honeycore", "app")
        for p in (BACKEND / root).rglob("*.py")
        if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


# --- (e) timing: right vs wrong password -------------------------------------------------


@pytest.mark.slow
def test_unlock_timing_right_vs_wrong_within_30_percent(vault: HoneyVault) -> None:
    runs = 20
    wrong = _random_passwords(runs)
    for pw in (MASTER, wrong[0]):  # warm-up (allocator, caches)
        vault.unlock(pw)
    right_t: list[float] = []
    wrong_t: list[float] = []
    for i in range(runs):  # interleave so drift affects both equally
        for pw, bucket in ((MASTER, right_t), (wrong[i], wrong_t)):
            start = time.perf_counter()
            vault.unlock(pw)
            bucket.append(time.perf_counter() - start)
    mean_right = sum(right_t) / runs
    mean_wrong = sum(wrong_t) / runs
    ratio = abs(mean_right - mean_wrong) / min(mean_right, mean_wrong)
    assert ratio < 0.30, f"right {mean_right * 1e3:.2f} ms vs wrong {mean_wrong * 1e3:.2f} ms"
