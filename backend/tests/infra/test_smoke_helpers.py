"""Unit tests for pure helper functions in scripts/smoke_test.py.

Owner: T4 — Vedant.
"""

from __future__ import annotations

import pytest

from scripts.smoke_test import (
    TestResult,
    format_results_table,
    generate_sample_entries,
    generate_smoke_credentials,
    has_failures,
    validate_health_response,
    validate_unlock_right,
    validate_unlock_wrong,
)


def test_generate_smoke_credentials() -> None:
    """Verify generated credentials meet length and inequality constraints."""
    username, login_pw, master_pw = generate_smoke_credentials("test_prefix")

    assert len(username) <= 32
    assert username.startswith("test_prefix_")
    assert login_pw != master_pw
    assert len(login_pw) >= 8
    assert len(master_pw) >= 8


def test_generate_sample_entries() -> None:
    """Verify sample entries return two valid, distinct entries."""
    entries = generate_sample_entries()
    assert len(entries) == 2
    for entry in entries:
        assert "service" in entry
        assert "username" in entry
        assert "password" in entry
    assert entries[0]["service"] != entries[1]["service"]


def test_validate_health_response_success() -> None:
    """Verify health validation passes when both API and honeychecker are ok."""
    payload = {
        "status": "ok",
        "version": "0.1.0",
        "honeycore_impl": "stub",
        "honeychecker": "ok",
    }
    ok, msg = validate_health_response(payload)
    assert ok is True
    assert "honeychecker=ok" in msg


@pytest.mark.parametrize(
    "payload,expected_substr",
    [
        ({"status": "error", "honeychecker": "ok"}, "API status is 'error'"),
        ({"status": "ok", "honeychecker": "down"}, "Honeychecker status is 'down'"),
        ({"status": "ok", "honeychecker": "unknown"}, "Honeychecker status is 'unknown'"),
        ("not-a-dict", "not a JSON object"),
    ],
)
def test_validate_health_response_failures(payload: dict | str, expected_substr: str) -> None:
    """Verify health validation fails when honeychecker or API status is not ok."""
    ok, msg = validate_health_response(payload)  # type: ignore[arg-type]
    assert ok is False
    assert expected_substr in msg


def test_validate_unlock_right_exact() -> None:
    """Verify correct master password unlock validation passes on exact match."""
    expected = generate_sample_entries()
    returned = [dict(e) for e in expected]

    ok, msg = validate_unlock_right(returned, expected)
    assert ok is True
    assert "match real values exactly" in msg


def test_validate_unlock_right_mismatch() -> None:
    """Verify correct master password unlock fails if values are altered."""
    expected = generate_sample_entries()
    tampered = [dict(e) for e in expected]
    tampered[0]["password"] = "tampered_password"  # noqa: S105

    ok, msg = validate_unlock_right(tampered, expected)
    assert ok is False
    assert "Password mismatch" in msg


def test_validate_unlock_right_count_mismatch() -> None:
    """Verify correct master password unlock fails if entry count differs."""
    expected = generate_sample_entries()
    ok, msg = validate_unlock_right([expected[0]], expected)
    assert ok is False
    assert "Entry count mismatch" in msg


def test_validate_unlock_wrong_valid_decoys() -> None:
    """Verify honey encryption requirement: wrong password returns plausible decoys."""
    real = generate_sample_entries()
    decoys = [
        {"service": "github.com", "username": "decoy_user_1", "password": "decoy_pass_abc"},
        {"service": "google.com", "username": "decoy_user_2", "password": "decoy_pass_def"},
    ]

    ok, msg = validate_unlock_wrong(decoys, real)
    assert ok is True
    assert "decoy entries returned" in msg


def test_validate_unlock_wrong_identical_fails() -> None:
    """Verify failure if wrong password returns real secrets (oracle flaw)."""
    real = generate_sample_entries()
    identical = [dict(e) for e in real]

    ok, msg = validate_unlock_wrong(identical, real)
    assert ok is False
    assert "returned authentic passwords" in msg


def test_validate_unlock_wrong_count_mismatch() -> None:
    """Verify wrong password must return identical entry count."""
    real = generate_sample_entries()
    ok, msg = validate_unlock_wrong([], real)
    assert ok is False
    assert "count mismatch" in msg


def test_format_results_table_and_has_failures() -> None:
    """Verify table rendering and failure detection logic."""
    results = [
        TestResult("Step 1", "PASS", "all good", 12.3),
        TestResult("Step 2", "SKIP", "not implemented", 0.0),
    ]
    assert has_failures(results) is False

    table_text = format_results_table(results)
    assert "Step 1" in table_text
    assert "PASS" in table_text
    assert "SKIP" in table_text
    assert "Summary: 1 passed, 1 skipped, 0 failed" in table_text

    results.append(TestResult("Step 3", "FAIL", "server error", 45.6))
    assert has_failures(results) is True
    updated_table = format_results_table(results)
    assert "Summary: 1 passed, 1 skipped, 1 failed" in updated_table
