"""Username DTE (67-int seed: email-domain choice + PCFG local part) (PROJECT-BRIEF.md §7.4).

Owner: T1 — Nidhi. Phase 2.

Seed layout (``USERNAME_SEED_INTS`` = 67 big-endian uint32, one per choice, see §7.2)::

    [email domain]  then a 66-int PCFG block laid out like the password DTE:
    PCFG path:     [path] [template] then per segment: [vocab-or-__CHARS__] [word | char x n]
    fallback path: [path] [length] [char x length]
    rest:          secrets.randbits(32) padding

Encode: if the username has exactly one ``@``, its domain is in the model's ``email_domains``
and the local part is 1..(32 - len(domain) - 1) chars, the domain is chosen and only the local
part goes through the PCFG; otherwise ``__NONE__`` is chosen and the whole username goes
through the PCFG (``@`` is a symbol).

Decode is TOTAL: domain choice, then the local part; when a domain was chosen, the local part
is truncated so ``local@domain`` fits 32 chars (domains are <= 30 chars, so >= 1 char stays).
"""

from __future__ import annotations

import secrets
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from honeycore.dte.int_codec import SeedReader, SeedWriter, decode_choice, encode_choice
from honeycore.dte.pcfg import (
    NO_DOMAIN,
    _build_dist,
    _PCFGBase,
    _validate_field,
    is_email_domain,
    split_email,
)
from honeycore.interfaces import INT_BYTES, MAX_FIELD_LEN, USERNAME_SEED_INTS

__all__ = ["DEFAULT_MODEL_PATH", "MODEL_ID", "PCFGUsernameModel"]

MODEL_ID = "pcfg-username-v1"
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pcfg_username_v1.json.gz"


class PCFGUsernameModel(_PCFGBase):
    """PCFG username model and DTE (``FieldDTE``, PROJECT-BRIEF.md §7.4).

    ``PCFGUsernameModel()`` / ``load_default()`` load ``pcfg_username_v1.json.gz``;
    ``from_file`` loads any model file; ``PCFGUsernameModel(model_dict)`` uses an
    already-parsed model (``kind`` must be ``"username"``).
    """

    kind = "username"
    default_model_path = DEFAULT_MODEL_PATH
    model_id: str = MODEL_ID
    seed_len: int = USERNAME_SEED_INTS * INT_BYTES

    def _load(self, model: Mapping[str, Any]) -> None:
        super()._load(model)
        domains = dict(model.get("email_domains") or {})
        if any(d != NO_DOMAIN and not is_email_domain(d) for d in domains):
            raise ValueError(f"email domains must be 1..{MAX_FIELD_LEN - 2} printable chars, no @")
        self._domains = _build_dist(domains, (NO_DOMAIN,))
        self._none_idx = self._domains.index_of(NO_DOMAIN)
        self._domain_set = frozenset(self._domains.symbols) - {NO_DOMAIN}

    # ---- FieldDTE -----------------------------------------------------------------------

    def encode(self, value: str) -> bytes:
        """Encode a 1..32-char printable username to a random ``seed_len``-byte seed.

        Raises:
            InvalidInputError: ``value`` is outside the §7.1 limits (the value is not echoed).
        """
        username = _validate_field(value, "username")
        domain, local = split_email(username, self._domain_set)
        w = SeedWriter()
        w.append(encode_choice(self._domains, self._domains.index_of(domain or NO_DOMAIN)))
        self._encode_block(w, local)
        return w.to_bytes(USERNAME_SEED_INTS)

    def decode(self, seed: bytes) -> str:
        """TOTAL: map any ``seed_len``-byte seed to a valid 1..32-char printable username.

        Raises:
            ValueError: only if ``len(seed) != seed_len``.
        """
        if len(seed) != self.seed_len:
            raise ValueError(f"username seed must be {self.seed_len} bytes")
        reader = SeedReader(seed)
        i = decode_choice(self._domains, reader.next())
        local = self._decode_block(reader)
        if i == self._none_idx:
            return local
        domain = self._domains.symbols[i]
        return f"{local[: MAX_FIELD_LEN - len(domain) - 1]}@{domain}"

    def sample(self) -> str:
        """Return ``decode(random seed)``: a username drawn from the model distribution."""
        return self.decode(secrets.token_bytes(self.seed_len))
