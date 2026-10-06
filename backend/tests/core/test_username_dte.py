"""Tests for ``honeycore.dte.username_dte`` (PROJECT-BRIEF.md §7.4). Owner: T1 — Nidhi.

Most tests use a small model trained (``pcfg.train_username_model``) on a fixed synthetic list
— never corpus lines in fixtures. Tests that need the real model or the held-out split skip
when those files are absent.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from honeycore.dte.int_codec import Distribution, SeedWriter, decode_choice, encode_choice
from honeycore.dte.password_dte import PCFGPasswordModel
from honeycore.dte.pcfg import (
    CHARS_TOKEN,
    EMAIL_DOMAINS,
    NO_DOMAIN,
    _PCFGBase,
    is_valid_field,
    load_model,
    save_model,
    split_email,
    template,
    train_username_model,
)
from honeycore.dte.username_dte import DEFAULT_MODEL_PATH, MODEL_ID, PCFGUsernameModel
from honeycore.interfaces import (
    MAX_FIELD_LEN,
    PASSWORD_SEED_INTS,
    USERNAME_SEED_INTS,
    FieldDTE,
    InvalidInputError,
)

REPO = Path(__file__).resolve().parents[3]
HELDOUT = REPO / "data" / "processed" / "heldout_usernames.tsv"
SEED_LEN = USERNAME_SEED_INTS * 4
DOMAINS = sorted(EMAIL_DOMAINS)

printable = st.characters(min_codepoint=0x20, max_codepoint=0x7E)
printable_text = st.text(alphabet=printable, min_size=1, max_size=MAX_FIELD_LEN)
known_emails = st.sampled_from(DOMAINS).flatmap(
    lambda d: st.text(alphabet=printable, min_size=1, max_size=MAX_FIELD_LEN - len(d) - 1).map(
        lambda local: f"{local}@{d}"
    )
)

# Synthetic training data: (username, count). Made up, not corpus lines.
_NAMES = ["alex", "sam", "jordan", "Taylor", "casey", "riley", "morgan", "jamie", "quinn", "drew"]
_TAILS = ["", "1", "7", "12", "99", "123", "2001", "_x", ".k", "_99"]


def _training_set() -> list[tuple[str, int]]:
    data: list[tuple[str, int]] = []
    for i, name in enumerate(_NAMES):
        for j, tail in enumerate(_TAILS):
            data.append((name + tail, 60 - 4 * i - 3 * j))
        data.append((name + "@gmail.com", 5))  # trained as the local part only
        data.append((name.upper(), 2))
    data += [("admin", 80), ("guest", 40), ("user", 50), ("test123", 20), ("root", 30)]
    return data


@pytest.fixture(scope="module")
def toy_dict() -> dict[str, Any]:
    return train_username_model(_training_set())


@pytest.fixture(scope="module")
def toy(toy_dict: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> PCFGUsernameModel:
    path = tmp_path_factory.mktemp("model") / "pcfg_username_v1.json.gz"
    save_model(toy_dict, path)
    return PCFGUsernameModel.from_file(path)


def _domain_choice(model_dict: dict[str, Any], seed: bytes) -> str:
    """The email-domain symbol selected by the seed's first int (same table as the DTE)."""
    dist = Distribution(model_dict["email_domains"])
    return dist.symbols[decode_choice(dist, int.from_bytes(seed[:4], "big"))]


def _uses_known_template(model_dict: dict[str, Any], username: str) -> bool:
    local = split_email(username, model_dict["email_domains"])[1]
    return template(local) in model_dict["templates"]


# --- basics --------------------------------------------------------------------------------


def test_protocol_and_constants(toy: PCFGUsernameModel) -> None:
    assert isinstance(toy, FieldDTE)
    assert isinstance(toy, _PCFGBase)
    assert toy.model_id == MODEL_ID == "pcfg-username-v1"
    assert toy.seed_len == SEED_LEN == 268
    assert USERNAME_SEED_INTS == PASSWORD_SEED_INTS + 1


def test_default_model_path_is_inside_package() -> None:
    assert DEFAULT_MODEL_PATH.parts[-3:] == ("honeycore", "models", "pcfg_username_v1.json.gz")


def test_encode_returns_seed_len(toy: PCFGUsernameModel) -> None:
    for u in ["admin", "alex@gmail.com", "~" * 32]:
        assert len(toy.encode(u)) == SEED_LEN


# --- encode / decode round trip ------------------------------------------------------------


@settings(max_examples=500, deadline=None)
@given(printable_text)
def test_roundtrip_any_printable(toy: PCFGUsernameModel, username: str) -> None:
    seed = toy.encode(username)
    assert len(seed) == SEED_LEN
    assert toy.decode(seed) == username


@settings(max_examples=300, deadline=None)
@given(known_emails)
def test_roundtrip_known_domain_emails(
    toy: PCFGUsernameModel, toy_dict: dict[str, Any], username: str
) -> None:
    seed = toy.encode(username)
    assert toy.decode(seed) == username
    local, domain = username.split("@", 1) if username.count("@") == 1 else ("", None)
    expected = domain if local else NO_DOMAIN  # a local part with "@" -> whole string, __NONE__
    assert _domain_choice(toy_dict, seed) == expected


@pytest.mark.parametrize(
    ("username", "domain"),
    [
        ("admin", NO_DOMAIN),
        ("alex@gmail.com", "gmail.com"),
        ("zz9@yahoo.co.in", "yahoo.co.in"),
        ("x" * 17 + "@rediffmail.com", "rediffmail.com"),  # 32 chars, longest local part
        ("alex@unknown.org", NO_DOMAIN),  # unknown domain: whole string via the PCFG
        ("a@b@gmail.com", NO_DOMAIN),  # two "@"
        ("@gmail.com", NO_DOMAIN),  # empty local part
        ("alex@Gmail.com", NO_DOMAIN),  # domains match exactly (case-sensitive)
        ("alex@__NONE__", NO_DOMAIN),
        ("alex@", NO_DOMAIN),
        (" ", NO_DOMAIN),
        ("~" * 32, NO_DOMAIN),
        ("a1" * 16, NO_DOMAIN),
    ],
)
def test_roundtrip_examples(
    toy: PCFGUsernameModel, toy_dict: dict[str, Any], username: str, domain: str
) -> None:
    seed = toy.encode(username)
    assert toy.decode(seed) == username
    assert _domain_choice(toy_dict, seed) == domain


def test_encode_is_randomised(toy: PCFGUsernameModel) -> None:
    a, b = toy.encode("alex@gmail.com"), toy.encode("alex@gmail.com")
    assert a != b
    assert toy.decode(a) == toy.decode(b) == "alex@gmail.com"


@pytest.mark.parametrize("bad", ["", "a" * 33, "tab\there", "new\nline", "josé", "\x7f"])
def test_encode_rejects_invalid(toy: PCFGUsernameModel, bad: str) -> None:
    with pytest.raises(InvalidInputError) as exc:
        toy.encode(bad)
    assert "username" in str(exc.value)
    if bad:
        assert bad not in str(exc.value)


def test_encode_rejects_non_str(toy: PCFGUsernameModel) -> None:
    with pytest.raises(InvalidInputError):
        toy.encode(None)  # type: ignore[arg-type]


# --- totality ------------------------------------------------------------------------------


def test_decode_is_total_on_random_seeds(toy: PCFGUsernameModel) -> None:
    for _ in range(5000):
        assert is_valid_field(toy.decode(secrets.token_bytes(SEED_LEN)))


@pytest.mark.parametrize("fill", [b"\x00", b"\xff", b"\x7f", b"\x80"])
def test_decode_is_total_on_constant_seeds(toy: PCFGUsernameModel, fill: bytes) -> None:
    assert is_valid_field(toy.decode(fill * SEED_LEN))


@settings(max_examples=300)
@given(st.binary(min_size=SEED_LEN, max_size=SEED_LEN))
def test_decode_is_total_hypothesis(toy: PCFGUsernameModel, seed: bytes) -> None:
    assert is_valid_field(toy.decode(seed))


@pytest.mark.parametrize("n", [0, 4, 264, SEED_LEN - 1, SEED_LEN + 1, 532])
def test_decode_rejects_wrong_length(toy: PCFGUsernameModel, n: int) -> None:
    with pytest.raises(ValueError):
        toy.decode(b"\x00" * n)


_LONG_LOCAL_MODEL: dict[str, Any] = {
    "version": 1,
    "kind": "username",
    "max_len": 32,
    "path": {"pcfg": 1, "fallback": 1},
    "templates": {"L32": 1},
    "segments": {"L": {"32": {CHARS_TOKEN: 1}}},
    "email_domains": {NO_DOMAIN: 1, "rediffmail.com": 1, "x" * 30: 1},
}


def test_decode_truncates_local_part_to_fit() -> None:
    m = PCFGUsernameModel(_LONG_LOCAL_MODEL)
    domains = Distribution(_LONG_LOCAL_MODEL["email_domains"])
    path = Distribution(_LONG_LOCAL_MODEL["path"])
    for domain, local_len in [("rediffmail.com", 17), ("x" * 30, 1)]:
        w = SeedWriter()
        w.append(encode_choice(domains, domains.index_of(domain)))
        w.append(encode_choice(path, path.index_of("pcfg")))  # template L32, chars random
        out = m.decode(w.to_bytes(USERNAME_SEED_INTS))
        assert len(out) == MAX_FIELD_LEN
        assert out == out[:local_len] + "@" + domain
        assert is_valid_field(out)


def test_decode_with_long_locals_is_total() -> None:
    m = PCFGUsernameModel(_LONG_LOCAL_MODEL)
    for _ in range(2000):
        assert is_valid_field(m.decode(secrets.token_bytes(SEED_LEN)))


def test_model_without_email_domains_uses_none_only() -> None:
    m = PCFGUsernameModel({k: v for k, v in _LONG_LOCAL_MODEL.items() if k != "email_domains"})
    for u in ["alex@gmail.com", "a" * 32, "x"]:
        assert m.decode(m.encode(u)) == u
    for _ in range(200):  # only __NONE__: the domain int never changes the output
        seed = secrets.token_bytes(SEED_LEN)
        assert m.decode(seed) == m.decode(secrets.token_bytes(4) + seed[4:])


# --- model validation ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "patch",
    [
        {"version": 2},
        {"kind": "password"},
        {"max_len": 16},
        {"templates": {}},
        {"templates": {"L3L2": 1}},
        {"segments": {"L": {"4": {"abc": 1}}}},
        {"email_domains": {NO_DOMAIN: 5, "a@b.com": 1}},
        {"email_domains": {NO_DOMAIN: 5, "x" * 31: 1}},
        {"email_domains": {NO_DOMAIN: 5, "": 1}},
        {"email_domains": {NO_DOMAIN: 5, "tab\t.com": 1}},
    ],
)
def test_malformed_models_rejected(toy_dict: dict[str, Any], patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        PCFGUsernameModel({**toy_dict, **patch})


def test_password_model_rejects_username_model(toy_dict: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        PCFGPasswordModel(toy_dict)


# --- sampling ------------------------------------------------------------------------------


def test_samples_use_known_templates(toy: PCFGUsernameModel, toy_dict: dict[str, Any]) -> None:
    samples = [toy.sample() for _ in range(1000)]
    assert all(is_valid_field(s) for s in samples)
    assert sum(_uses_known_template(toy_dict, s) for s in samples) >= 900
    emails = sum(split_email(s, EMAIL_DOMAINS)[0] is not None for s in samples)
    assert 300 <= emails <= 600  # __NONE__ is ~55% of the domain table
    assert len(set(samples)) > 100


# --- real model / held-out data (skip until trained) ---------------------------------------

needs_default = pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(), reason="username model not trained yet (train_pcfg.py)"
)


@pytest.fixture(scope="module")
def default_model() -> PCFGUsernameModel:
    return PCFGUsernameModel.load_default()


@pytest.fixture(scope="module")
def default_dict() -> dict[str, Any]:
    return load_model(DEFAULT_MODEL_PATH)


@needs_default
def test_default_model_loads_and_is_total(default_model: PCFGUsernameModel) -> None:
    assert default_model.model_id == MODEL_ID
    assert isinstance(default_model, FieldDTE)
    for _ in range(5000):
        assert is_valid_field(default_model.decode(secrets.token_bytes(SEED_LEN)))


@needs_default
def test_default_model_has_domain_table(default_dict: dict[str, Any]) -> None:
    assert default_dict["kind"] == "username"
    assert list(default_dict["email_domains"])[0] == NO_DOMAIN
    assert len(default_dict["email_domains"]) >= 31


@needs_default
@settings(max_examples=200, deadline=None)
@given(st.one_of(printable_text, known_emails))
def test_default_model_roundtrip(default_model: PCFGUsernameModel, username: str) -> None:
    assert default_model.decode(default_model.encode(username)) == username


@needs_default
def test_default_model_samples_use_known_templates(
    default_model: PCFGUsernameModel, default_dict: dict[str, Any]
) -> None:
    samples = [default_model.sample() for _ in range(1000)]
    assert sum(_uses_known_template(default_dict, s) for s in samples) >= 900


@needs_default
@pytest.mark.skipif(not HELDOUT.exists(), reason="held-out usernames not generated yet")
def test_heldout_roundtrip(default_model: PCFGUsernameModel) -> None:
    usernames: list[str] = []
    with HELDOUT.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            u = line.rstrip("\r\n").split("\t", 1)[0]
            if is_valid_field(u):
                usernames.append(u)
            if len(usernames) == 2000:
                break
    assert usernames
    # Count failures without echoing corpus usernames into the test report.
    failures = sum(default_model.decode(default_model.encode(u)) != u for u in usernames)
    assert failures == 0
