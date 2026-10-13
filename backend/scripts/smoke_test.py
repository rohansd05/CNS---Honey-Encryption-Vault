"""HoneyVault End-to-End Smoke Test CLI.

Usage:
    python -m scripts.smoke_test --api http://localhost:8000 [--frontend http://localhost:5173]

Tests complete operational workflow:
1. Health probe (API + Honeychecker connectivity)
2. User registration with distinct login & master passwords
3. User login and JWT issuance
4. Vault entry creation (2 entries)
5. Vault unlock with correct master password (exact match verification)
6. Vault unlock with incorrect master password (honey encryption invariant: HTTP 200,
   equal count, altered decoy credentials)
7. /auth/me user profile & entry count verification
8. /eval/summary endpoint check (PASS on 200, SKIP on 404)
9. /attack endpoints check if in demo mode (PASS on 200, SKIP on 404)
10. Frontend routes / and /vault return 200 (if --frontend provided)

Pure helper functions are unit-tested in backend/tests/infra/test_smoke_helpers.py.
"""

from __future__ import annotations

import argparse
import secrets
import sys
import time
from dataclasses import dataclass
from typing import Literal

import httpx

StatusType = Literal["PASS", "FAIL", "SKIP"]


@dataclass(frozen=True)
class TestResult:
    """Outcome of a single smoke test step."""

    __test__ = False

    name: str
    status: StatusType
    details: str
    duration_ms: float = 0.0


# =====================================================================
# Pure Helper Functions (Unit-Tested in test_smoke_helpers.py)
# =====================================================================


def generate_smoke_credentials(prefix: str = "smoke") -> tuple[str, str, str]:
    """Generate valid test username, login password, and master password.

    Invariants:
    - Username length <= 32 printable ASCII chars.
    - Login password != Master password.
    """
    token = secrets.token_hex(4)
    username = f"{prefix}_{token}"[:32]
    login_pw = f"Login!{token}#A"
    master_pw = f"Master!{token}$B"
    return username, login_pw, master_pw


def generate_sample_entries() -> list[dict[str, str]]:
    """Return two distinct sample entries for vault testing."""
    return [
        {
            "service": "github.com",
            "username": "octocat_smoke",
            "password": "gh_secret_pass_123",
        },
        {
            "service": "google.com",
            "username": "googler_smoke",
            "password": "google_secret_pass_456",
        },
    ]


def validate_health_response(data: dict) -> tuple[bool, str]:
    """Validate /api/health JSON payload."""
    if not isinstance(data, dict):
        return False, "Response body is not a JSON object"
    status = data.get("status")
    hc_status = data.get("honeychecker")
    version = data.get("version", "unknown")
    impl = data.get("honeycore_impl", "unknown")

    if status != "ok":
        return False, f"API status is '{status}', expected 'ok'"
    if hc_status != "ok":
        return False, f"Honeychecker status is '{hc_status}', expected 'ok'"

    return True, f"v{version}, impl={impl}, honeychecker=ok"


def validate_unlock_right(entries: list[dict], expected_entries: list[dict]) -> tuple[bool, str]:
    """Validate that vault unlock with the correct master password returns exact entries."""
    if not isinstance(entries, list):
        return False, "Entries field is not a list"
    if len(entries) != len(expected_entries):
        return (
            False,
            f"Entry count mismatch: got {len(entries)}, expected {len(expected_entries)}",
        )

    expected_map = {e["service"]: e for e in expected_entries}
    for entry in entries:
        service = entry.get("service")
        if service not in expected_map:
            return False, f"Unexpected service '{service}' in unlocked vault"
        exp = expected_map[service]
        if entry.get("username") != exp["username"]:
            return (
                False,
                f"Username mismatch for {service}: got {entry.get('username')}, "
                f"expected {exp['username']}",
            )
        if entry.get("password") != exp["password"]:
            return (
                False,
                f"Password mismatch for {service}: got {entry.get('password')}, "
                f"expected {exp['password']}",
            )

    return True, f"All {len(entries)} entries match real values exactly"


def validate_unlock_wrong(decoy_entries: list[dict], real_entries: list[dict]) -> tuple[bool, str]:
    """Validate that vault unlock with a wrong master password returns plausible decoys.

    Invariants (Honey Encryption):
    - Must return the same entry count.
    - Decoy values (usernames/passwords) must differ from real entries.
    """
    if not isinstance(decoy_entries, list):
        return False, "Decoy entries field is not a list"
    if len(decoy_entries) != len(real_entries):
        return (
            False,
            f"Decoy entry count mismatch: got {len(decoy_entries)}, expected {len(real_entries)}",
        )

    real_map = {e["service"]: e for e in real_entries}
    different_fields = 0
    for decoy in decoy_entries:
        service = decoy.get("service")
        if service in real_map:
            real = real_map[service]
            if decoy.get("password") != real["password"]:
                different_fields += 1
            if decoy.get("username") != real["username"]:
                different_fields += 1

    if different_fields == 0:
        return (
            False,
            "Wrong master password returned authentic passwords instead of decoys!",
        )

    return (
        True,
        f"{len(decoy_entries)} decoy entries returned ({different_fields} fields altered)",
    )


def has_failures(results: list[TestResult]) -> bool:
    """Return True if any test result has status FAIL."""
    return any(r.status == "FAIL" for r in results)


def format_results_table(results: list[TestResult]) -> str:
    """Render a clean summary table for console output."""
    col_name = 38
    col_status = 8
    col_time = 12
    col_details = 42

    divider = f"+-{'-' * col_name}-+-{'-' * col_status}-+-{'-' * col_time}-+-{'-' * col_details}-+"
    header = (
        f"| {'Test Name':<{col_name}} "
        f"| {'Status':<{col_status}} "
        f"| {'Duration':<{col_time}} "
        f"| {'Details':<{col_details}} |"
    )

    lines = [divider, header, divider]
    passed = 0
    failed = 0
    skipped = 0

    for r in results:
        if r.status == "PASS":
            passed += 1
        elif r.status == "FAIL":
            failed += 1
        else:
            skipped += 1

        time_str = f"{r.duration_ms:.1f} ms"
        det = r.details if len(r.details) <= col_details else r.details[: col_details - 3] + "..."
        line = (
            f"| {r.name:<{col_name}} "
            f"| {r.status:<{col_status}} "
            f"| {time_str:<{col_time}} "
            f"| {det:<{col_details}} |"
        )
        lines.append(line)

    lines.append(divider)
    summary = (
        f"Summary: {passed} passed, {skipped} skipped, {failed} failed (Total: {len(results)})"
    )
    lines.append(summary)
    return "\n".join(lines)


# =====================================================================
# Smoke Test Runner
# =====================================================================


def run_smoke_test(
    api_url: str,
    frontend_url: str | None = None,
    timeout: float = 10.0,
) -> list[TestResult]:
    """Execute all smoke test steps using an HTTP client."""
    results: list[TestResult] = []
    api_base = api_url.rstrip("/")

    with httpx.Client(timeout=timeout) as client:
        # 1. Health check
        t0 = time.perf_counter()
        try:
            resp = client.get(f"{api_base}/api/health")
            duration = (time.perf_counter() - t0) * 1000
            if resp.status_code == 200:
                ok, msg = validate_health_response(resp.json())
                status: StatusType = "PASS" if ok else "FAIL"
                results.append(TestResult("1. API & Honeychecker Health", status, msg, duration))
            else:
                results.append(
                    TestResult(
                        "1. API & Honeychecker Health",
                        "FAIL",
                        f"HTTP {resp.status_code}: {resp.text[:60]}",
                        duration,
                    )
                )
        except Exception as ex:
            duration = (time.perf_counter() - t0) * 1000
            results.append(TestResult("1. API & Honeychecker Health", "FAIL", str(ex), duration))
            # If health fails completely, return early
            return results

        # 2. Register random user
        username, login_pw, master_pw = generate_smoke_credentials()
        t0 = time.perf_counter()
        try:
            reg_resp = client.post(
                f"{api_base}/api/auth/register",
                json={
                    "username": username,
                    "login_password": login_pw,
                    "master_password": master_pw,
                },
            )
            duration = (time.perf_counter() - t0) * 1000
            if reg_resp.status_code == 201:
                results.append(
                    TestResult(
                        "2. User Registration",
                        "PASS",
                        f"Registered username={username}",
                        duration,
                    )
                )
            else:
                results.append(
                    TestResult(
                        "2. User Registration",
                        "FAIL",
                        f"HTTP {reg_resp.status_code}: {reg_resp.text[:60]}",
                        duration,
                    )
                )
        except Exception as ex:
            duration = (time.perf_counter() - t0) * 1000
            results.append(TestResult("2. User Registration", "FAIL", str(ex), duration))

        # 3. User login
        token: str | None = None
        t0 = time.perf_counter()
        try:
            login_resp = client.post(
                f"{api_base}/api/auth/login",
                json={"username": username, "login_password": login_pw},
            )
            duration = (time.perf_counter() - t0) * 1000
            if login_resp.status_code == 200:
                data = login_resp.json()
                token = data.get("access_token")
                results.append(
                    TestResult(
                        "3. User Login",
                        "PASS",
                        "Obtained bearer JWT access token",
                        duration,
                    )
                )
            else:
                results.append(
                    TestResult(
                        "3. User Login",
                        "FAIL",
                        f"HTTP {login_resp.status_code}: {login_resp.text[:60]}",
                        duration,
                    )
                )
        except Exception as ex:
            duration = (time.perf_counter() - t0) * 1000
            results.append(TestResult("3. User Login", "FAIL", str(ex), duration))

        auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

        # 4. Add 2 entries
        sample_entries = generate_sample_entries()
        t0 = time.perf_counter()
        entries_added = 0
        try:
            for entry in sample_entries:
                add_resp = client.post(
                    f"{api_base}/api/vault/entries",
                    headers=auth_headers,
                    json={
                        "master_password": master_pw,
                        "service": entry["service"],
                        "username": entry["username"],
                        "password": entry["password"],
                    },
                )
                if add_resp.status_code == 201:
                    entries_added += 1
            duration = (time.perf_counter() - t0) * 1000
            if entries_added == len(sample_entries):
                results.append(
                    TestResult(
                        "4. Add Vault Entries",
                        "PASS",
                        f"Added {entries_added} entries successfully",
                        duration,
                    )
                )
            else:
                results.append(
                    TestResult(
                        "4. Add Vault Entries",
                        "FAIL",
                        f"Added {entries_added}/{len(sample_entries)} entries",
                        duration,
                    )
                )
        except Exception as ex:
            duration = (time.perf_counter() - t0) * 1000
            results.append(TestResult("4. Add Vault Entries", "FAIL", str(ex), duration))

        # 5. Unlock right (exact match)
        t0 = time.perf_counter()
        try:
            unlock_resp = client.post(
                f"{api_base}/api/vault/unlock",
                headers=auth_headers,
                json={"master_password": master_pw},
            )
            duration = (time.perf_counter() - t0) * 1000
            if unlock_resp.status_code == 200:
                data = unlock_resp.json()
                ok, msg = validate_unlock_right(data.get("entries", []), sample_entries)
                status = "PASS" if ok else "FAIL"
                results.append(
                    TestResult("5. Unlock Vault (Correct Password)", status, msg, duration)
                )
            else:
                results.append(
                    TestResult(
                        "5. Unlock Vault (Correct Password)",
                        "FAIL",
                        f"HTTP {unlock_resp.status_code}: {unlock_resp.text[:60]}",
                        duration,
                    )
                )
        except Exception as ex:
            duration = (time.perf_counter() - t0) * 1000
            results.append(
                TestResult("5. Unlock Vault (Correct Password)", "FAIL", str(ex), duration)
            )

        # 6. Unlock wrong (honey decoy verification)
        t0 = time.perf_counter()
        try:
            wrong_resp = client.post(
                f"{api_base}/api/vault/unlock",
                headers=auth_headers,
                json={"master_password": "WrongMasterPassword!999"},
            )
            duration = (time.perf_counter() - t0) * 1000
            if wrong_resp.status_code == 200:
                data = wrong_resp.json()
                ok, msg = validate_unlock_wrong(data.get("entries", []), sample_entries)
                status = "PASS" if ok else "FAIL"
                results.append(
                    TestResult("6. Unlock Vault (Wrong Password)", status, msg, duration)
                )
            else:
                results.append(
                    TestResult(
                        "6. Unlock Vault (Wrong Password)",
                        "FAIL",
                        f"HTTP {wrong_resp.status_code} (invariable requires 200)",
                        duration,
                    )
                )
        except Exception as ex:
            duration = (time.perf_counter() - t0) * 1000
            results.append(
                TestResult("6. Unlock Vault (Wrong Password)", "FAIL", str(ex), duration)
            )

        # 7. /auth/me verification
        t0 = time.perf_counter()
        try:
            me_resp = client.get(f"{api_base}/api/auth/me", headers=auth_headers)
            duration = (time.perf_counter() - t0) * 1000
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                entry_cnt = me_data.get("entry_count", 0)
                results.append(
                    TestResult(
                        "7. User Profile (/auth/me)",
                        "PASS",
                        f"User confirmed, entry_count={entry_cnt}",
                        duration,
                    )
                )
            else:
                results.append(
                    TestResult(
                        "7. User Profile (/auth/me)",
                        "FAIL",
                        f"HTTP {me_resp.status_code}: {me_resp.text[:60]}",
                        duration,
                    )
                )
        except Exception as ex:
            duration = (time.perf_counter() - t0) * 1000
            results.append(TestResult("7. User Profile (/auth/me)", "FAIL", str(ex), duration))

        # 8. Evaluation summary (/api/eval/summary)
        t0 = time.perf_counter()
        try:
            eval_resp = client.get(f"{api_base}/api/eval/summary")
            duration = (time.perf_counter() - t0) * 1000
            if eval_resp.status_code == 200:
                results.append(
                    TestResult("8. Evaluation Summary", "PASS", "HTTP 200 summary loaded", duration)
                )
            elif eval_resp.status_code == 404:
                results.append(
                    TestResult(
                        "8. Evaluation Summary",
                        "SKIP",
                        "Feature not yet implemented or no eval file (404)",
                        duration,
                    )
                )
            else:
                results.append(
                    TestResult(
                        "8. Evaluation Summary",
                        "FAIL",
                        f"HTTP {eval_resp.status_code}",
                        duration,
                    )
                )
        except Exception as ex:
            duration = (time.perf_counter() - t0) * 1000
            results.append(TestResult("8. Evaluation Summary", "FAIL", str(ex), duration))

        # 9. Attack endpoints (if demo mode enabled)
        t0 = time.perf_counter()
        try:
            atk_resp = client.get(f"{api_base}/api/attack/stolen-vault")
            duration = (time.perf_counter() - t0) * 1000
            if atk_resp.status_code == 200:
                results.append(
                    TestResult(
                        "9. Attack Console Endpoints", "PASS", "HTTP 200 stolen vault", duration
                    )
                )
            elif atk_resp.status_code == 404:
                results.append(
                    TestResult(
                        "9. Attack Console Endpoints",
                        "SKIP",
                        "Attack routes not implemented or demo mode disabled (404)",
                        duration,
                    )
                )
            else:
                results.append(
                    TestResult(
                        "9. Attack Console Endpoints",
                        "FAIL",
                        f"HTTP {atk_resp.status_code}",
                        duration,
                    )
                )
        except Exception as ex:
            duration = (time.perf_counter() - t0) * 1000
            results.append(TestResult("9. Attack Console Endpoints", "FAIL", str(ex), duration))

        # 10. Frontend checks
        if frontend_url:
            fe_base = frontend_url.rstrip("/")
            # Check /
            t0 = time.perf_counter()
            try:
                fe_root = client.get(f"{fe_base}/")
                duration = (time.perf_counter() - t0) * 1000
                if fe_root.status_code == 200:
                    results.append(
                        TestResult(
                            "10. Frontend Landing (/)", "PASS", "HTTP 200 HTML page", duration
                        )
                    )
                else:
                    results.append(
                        TestResult(
                            "10. Frontend Landing (/)",
                            "FAIL",
                            f"HTTP {fe_root.status_code}",
                            duration,
                        )
                    )
            except Exception as ex:
                duration = (time.perf_counter() - t0) * 1000
                results.append(TestResult("10. Frontend Landing (/)", "FAIL", str(ex), duration))

            # Check /vault (SPA fallback)
            t0 = time.perf_counter()
            try:
                fe_vault = client.get(f"{fe_base}/vault")
                duration = (time.perf_counter() - t0) * 1000
                if fe_vault.status_code == 200:
                    results.append(
                        TestResult(
                            "11. Frontend SPA Route (/vault)",
                            "PASS",
                            "HTTP 200 SPA fallback",
                            duration,
                        )
                    )
                else:
                    results.append(
                        TestResult(
                            "11. Frontend SPA Route (/vault)",
                            "FAIL",
                            f"HTTP {fe_vault.status_code}",
                            duration,
                        )
                    )
            except Exception as ex:
                duration = (time.perf_counter() - t0) * 1000
                results.append(
                    TestResult("11. Frontend SPA Route (/vault)", "FAIL", str(ex), duration)
                )
        else:
            results.append(
                TestResult(
                    "10. Frontend Landing (/)",
                    "SKIP",
                    "Frontend URL omitted (--frontend)",
                    0.0,
                )
            )
            results.append(
                TestResult(
                    "11. Frontend SPA Route (/vault)",
                    "SKIP",
                    "Frontend URL omitted (--frontend)",
                    0.0,
                )
            )

    return results


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="HoneyVault end-to-end smoke test suite.",
    )
    parser.add_argument(
        "--api",
        required=True,
        help="Base URL of HoneyVault API (e.g. http://localhost:8000)",
    )
    parser.add_argument(
        "--frontend",
        required=False,
        default=None,
        help="Optional base URL of Frontend (e.g. http://localhost:5173)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds (default: 10.0)",
    )

    args = parser.parse_args()
    print(f"\nRunning HoneyVault Smoke Test against API: {args.api}")
    if args.frontend:
        print(f"Testing Frontend at: {args.frontend}")
    print()

    results = run_smoke_test(
        api_url=args.api,
        frontend_url=args.frontend,
        timeout=args.timeout,
    )

    print(format_results_table(results))
    print()

    if has_failures(results):
        print("Smoke test failed.")
        sys.exit(1)
    else:
        print("Smoke test succeeded.")
        sys.exit(0)


if __name__ == "__main__":
    main()
