"""Tests for secret and insecure logging auditor.

Ensures:
- Synthetic git repository testing in isolated tmp_path without touching real config.
- AST logging checks differentiate plain string messages from sensitive expressions.
- Report findings never contain secret matched text.
- Detection of PEM private keys, Base64 markers, database passwords, and committed .env files.
- audit_secrets.py and test_audit_secrets.py do not trip their own audit.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.audit_secrets import (
    ALLOWLIST_RULES,
    Finding,
    format_table,
    is_allowlisted_finding,
    is_allowlisted_path,
    is_sensitive_file_path,
    main,
    scan_git_history,
    scan_line_for_secrets,
    scan_python_code_ast,
    scan_working_tree,
)


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Path:
    """Create a temporary throwaway git repository with local user config only."""
    repo_dir = tmp_path / "synthetic_repo"
    repo_dir.mkdir()
    git_bin = shutil.which("git") or "git"

    subprocess.run([git_bin, "init"], cwd=repo_dir, check=True, capture_output=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        [git_bin, "config", "user.name", "Synthetic Auditor"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(  # noqa: S603
        [git_bin, "config", "user.email", "auditor@synthetic.local"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    return repo_dir


def test_pem_private_key_and_base64_markers():
    """Verify detection of PEM private key and Base64-encoded BEGIN markers."""
    pem_marker = "-----" + "BEGIN" + " PRIVATE KEY-----"
    findings = scan_line_for_secrets(
        content=f"PRIVATE_KEY = '{pem_marker}'",
        file_path="config.env",
        line_no=10,
    )
    assert len(findings) == 1
    assert findings[0].rule == "private-key"
    assert findings[0].file == "config.env"
    assert findings[0].line == 10

    b64_marker = "LS0tLS1C" + "RUdJTi" + "MIIEvgIBADANBgk"
    findings_b64 = scan_line_for_secrets(
        content=f"BLOB = '{b64_marker}'",
        file_path="keys.txt",
        line_no=2,
    )
    assert len(findings_b64) == 1
    assert findings_b64[0].rule == "private-key"


def test_committed_sensitive_file_extensions_and_env():
    """Verify detection of committed .env files and sensitive key/certificate extensions."""
    assert is_sensitive_file_path(".env") is True
    assert is_sensitive_file_path("backend/.env") is True
    assert is_sensitive_file_path("config/.env.production") is True
    assert is_sensitive_file_path(".env.example") is False
    assert is_sensitive_file_path("certs/server.key") is True
    assert is_sensitive_file_path("keys/id_rsa.pem") is True
    assert is_sensitive_file_path("pki/bundle.p12") is True
    assert is_sensitive_file_path("app/main.py") is False


def test_postgres_url_passwords_and_placeholders():
    """Verify PostgreSQL URL password detection while ignoring safe placeholders."""
    scheme = "post" + "gres"
    auth = "appuser:realproductionpassword12345"
    real_uri = f"{scheme}://" + f"{auth}@db.internal:5432/proddb"
    findings = scan_line_for_secrets(
        content=f"DATABASE_URL = '{real_uri}'",
        file_path="backend/.env",
        line_no=5,
    )
    assert len(findings) == 1
    assert findings[0].rule == "database-password"

    dummy_auth = "USER:PASSWORD"
    dummy_uri = f"{scheme}://" + f"{dummy_auth}@ep-xxxx.aws.neon.tech/honeyvault?sslmode=require"
    findings_dummy = scan_line_for_secrets(
        content=f"# {dummy_uri}",
        file_path=".env.example",
        line_no=20,
    )
    assert len(findings_dummy) == 0


def test_secret_assignment_and_safe_placeholders():
    """Verify detection of JWT_SECRET and KEY_WRAP_SECRET non-placeholder assignments."""
    prefix_jwt = "JWT_" + "SECRET"
    findings = scan_line_for_secrets(
        content=f"{prefix_jwt} = 'supersecretlongtokenstring12345'",
        file_path="app/config.py",
        line_no=8,
    )
    assert len(findings) == 1
    assert findings[0].rule == "hardcoded-secret"

    prefix_kw = "KEY_WRAP_" + "SECRET"
    findings_kw = scan_line_for_secrets(
        content=f"{prefix_kw} = 'c29tZXNlY3JldGtleXdyYXAxMjM0NTY3ODkwMTI='",
        file_path="app/config.py",
        line_no=9,
    )
    assert len(findings_kw) == 1
    assert findings_kw[0].rule == "hardcoded-secret"

    # Placeholder values must not be flagged
    findings_placeholder = scan_line_for_secrets(
        content=f"{prefix_jwt}=change-me",
        file_path=".env.example",
        line_no=23,
    )
    assert len(findings_placeholder) == 0


def test_git_history_detection_isolated_repo(synthetic_repo: Path):
    """Verify git history detection with commit hash attribution in an isolated repo."""
    git_bin = shutil.which("git") or "git"

    # Clean initial commit
    (synthetic_repo / "main.py").write_text("print('Clean start')\n", encoding="utf-8")
    subprocess.run([git_bin, "add", "main.py"], cwd=synthetic_repo, check=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        [git_bin, "commit", "-m", "Initial clean commit"],
        cwd=synthetic_repo,
        check=True,
    )
    assert list(scan_git_history(synthetic_repo)) == []

    # Commit with sensitive key
    pem_marker = "-----" + "BEGIN" + " PRIVATE KEY-----"
    (synthetic_repo / "server.key").write_text(f"{pem_marker}\nABCDEF1234\n", encoding="utf-8")
    subprocess.run([git_bin, "add", "server.key"], cwd=synthetic_repo, check=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        [git_bin, "commit", "-m", "Commit key leak"],
        cwd=synthetic_repo,
        check=True,
    )

    findings = list(scan_git_history(synthetic_repo))
    assert len(findings) >= 1
    key_findings = [f for f in findings if f.file == "server.key"]
    assert len(key_findings) >= 1
    assert key_findings[0].rule in ("private-key", "committed-files")
    assert key_findings[0].commit is not None
    assert len(key_findings[0].commit) == 40


def test_git_history_added_vs_removed_lines(synthetic_repo: Path):
    """Verify removed lines are not treated as new leaks and deleted secrets remain flagged."""
    git_bin = shutil.which("git") or "git"
    pem_marker = "-----" + "BEGIN" + " PRIVATE KEY-----"
    key_path = synthetic_repo / "secret.pem"
    key_path.write_text(f"{pem_marker}\nXYZ123\n", encoding="utf-8")
    subprocess.run([git_bin, "add", "secret.pem"], cwd=synthetic_repo, check=True)  # noqa: S603
    subprocess.run([git_bin, "commit", "-m", "Add secret"], cwd=synthetic_repo, check=True)  # noqa: S603

    findings_before = list(scan_git_history(synthetic_repo))
    commit_add = findings_before[0].commit

    # Remove secret
    key_path.unlink()
    subprocess.run([git_bin, "rm", "secret.pem"], cwd=synthetic_repo, check=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        [git_bin, "commit", "-m", "Remove secret"],
        cwd=synthetic_repo,
        check=True,
    )

    findings_after = list(scan_git_history(synthetic_repo))
    # Must still attribute leak to the adding commit, not the deletion commit
    assert any(f.commit == commit_add for f in findings_after)


def test_working_tree_detection(tmp_path: Path):
    """Verify working tree scanning detects secrets and committed files."""
    proj = tmp_path / "worktree_proj"
    proj.mkdir()
    (proj / "safe.py").write_text("print('All clear')\n", encoding="utf-8")

    prefix = "JWT_" + "SECRET"
    (proj / "app_config.py").write_text(
        f"{prefix} = 'thisisarealleakedjwtsecret12345'\n", encoding="utf-8"
    )

    findings = scan_working_tree(proj)
    assert len(findings) == 1
    assert findings[0].rule == "hardcoded-secret"
    assert findings[0].file == "app_config.py"


def test_sensitive_logging_and_print_ast():
    """Verify AST logging inspection for all 5 terms:
    password, master, sweetword, seed, key_wrap.
    """
    code = """
import logging
logger = logging.getLogger(__name__)

# Line 6: password
logger.info("Login", password=user_pass)

# Line 9: master
print(f"Master key: {master_key}")

# Line 12: sweetword
logger.warning("Decoy triggered", sweetword=decoy_val)

# Line 15: seed
print("Vault seed:", entry_seed)

# Line 18: key_wrap
logger.error("KEK:", key_wrap_secret)
"""
    findings = scan_python_code_ast(code, file_path="backend/app/auth.py")
    assert len(findings) == 5
    for f in findings:
        assert f.rule == "sensitive-logging"
        assert f.file == "backend/app/auth.py"
    lines = {f.line for f in findings}
    assert lines == {6, 9, 12, 15, 18}


def test_sensitive_logging_plain_string_and_harmless_calls_not_flagged():
    """Verify plain string messages, len() calls, and index suffixes are NOT flagged."""
    code = """
import logging
logger = logging.getLogger(__name__)

# Plain strings discussing sensitive topics
logger.info("Invalid password format")
print("Password must be at least 12 characters")
logger.warning("Master password mismatch")
print("Sweetword verification succeeded")

# Metadata calls and indices
logger.info("Count: %d", len(sweetwords))
print("Password length:", len(password))
logger.warning("Tripwire alarm at index %d", sweetword_index)
"""
    findings = scan_python_code_ast(code, file_path="backend/app/services.py")
    assert len(findings) == 0


def test_allowlist_safe_cases_and_narrowness():
    """Verify allowlist covers documented mock/demo cases and does not hide real leaks."""
    # Documentation example AWS key
    f_vault = Finding(
        rule="cloud-token",
        file="frontend/src/mocks/handlers/vault.ts",
        line=35,
    )
    assert is_allowlisted_finding(f_vault) is True

    # Real leak in another file must NOT be allowlisted
    f_real_vault = Finding(rule="cloud-token", file="backend/app/main.py", line=35)
    assert is_allowlisted_finding(f_real_vault) is False

    # Mock session tokens
    f_auth_demo = Finding(
        rule="hardcoded-secret",
        file="frontend/src/mocks/handlers/auth.ts",
        line=36,
    )
    assert is_allowlisted_finding(f_auth_demo) is True

    # Local CLI demo setup printing master password
    f_seed = Finding(
        rule="sensitive-logging",
        file="backend/scripts/seed_demo.py",
        line=116,
    )
    assert is_allowlisted_finding(f_seed) is True

    # Same rule in another file must NOT be allowlisted
    f_other_log = Finding(
        rule="sensitive-logging",
        file="backend/app/auth.py",
        line=116,
    )
    assert is_allowlisted_finding(f_other_log) is False

    # Check path allowlist
    assert is_allowlisted_path("backend/scripts/audit_secrets.py") is True
    assert is_allowlisted_path("backend/tests/infra/test_audit_secrets.py") is True
    assert is_allowlisted_path("backend/app/main.py") is False
    assert len(ALLOWLIST_RULES) == 6


def test_output_table_and_exit_codes():
    """Verify output table formatting and exit code logic."""
    results_pass = {
        "committed-files": (0, True),
        "sensitive-logging": (0, True),
        "working-tree": (0, True),
        "git-history": (0, True),
    }
    table_pass = format_table(results_pass)
    assert "check" in table_pass
    assert "findings" in table_pass
    assert "PASS/FAIL" in table_pass
    assert "| PASS" in table_pass
    assert "| FAIL" not in table_pass

    results_fail = {
        "committed-files": (1, False),
        "sensitive-logging": (0, True),
        "working-tree": (0, True),
        "git-history": (0, True),
    }
    table_fail = format_table(results_fail)
    assert "| FAIL" in table_fail


def test_git_errors_and_timeout_fail_safely(synthetic_repo: Path):
    """Verify git timeout triggers TimeoutError safely without dumping raw git stream."""
    git_bin = shutil.which("git") or "git"
    (synthetic_repo / "f.txt").write_text("content\n", encoding="utf-8")
    subprocess.run([git_bin, "add", "f.txt"], cwd=synthetic_repo, check=True)  # noqa: S603
    subprocess.run([git_bin, "commit", "-m", "c1"], cwd=synthetic_repo, check=True)  # noqa: S603

    with pytest.raises(TimeoutError):
        list(scan_git_history(synthetic_repo, timeout=0.00000001))


def test_no_output_contains_synthetic_secret_values():
    """Verify Finding objects and formatted representations never store secret content."""
    finding = Finding(
        rule="private-key",
        file="secrets.env",
        line=14,
        commit="d8f631263e6c25f42e801504fa18d1afdf54fc58",
    )
    rendered = str(finding)
    assert "[private-key] secrets.env:14" in rendered
    assert hasattr(finding, "rule")
    assert hasattr(finding, "file")
    assert hasattr(finding, "line")
    assert hasattr(finding, "commit")
    assert not hasattr(finding, "secret")
    assert not hasattr(finding, "matched_text")
    assert not hasattr(finding, "content")


def test_auditor_self_scan_clean():
    """Verify audit_secrets.py and test_audit_secrets.py produce 0 findings on direct scan."""
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "backend" / "scripts" / "audit_secrets.py"
    test_path = repo_root / "backend" / "tests" / "infra" / "test_audit_secrets.py"

    assert script_path.is_file(), f"Missing {script_path}"
    assert test_path.is_file(), f"Missing {test_path}"

    for target in (script_path, test_path):
        text = target.read_text(encoding="utf-8")
        # Direct AST check
        ast_f = scan_python_code_ast(text, file_path=target.as_posix())
        assert ast_f == [], f"Direct AST finding in {target}: {ast_f}"

        # Direct line-by-line check
        line_f: list[Finding] = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            line_f.extend(
                scan_line_for_secrets(
                    content=line,
                    file_path=target.as_posix(),
                    line_no=line_no,
                )
            )
        assert line_f == [], f"Direct line finding in {target}: {line_f}"


def test_main_cli_returns_zero_on_actual_repo():
    """Verify main() CLI execution on the actual repository completes successfully."""
    repo_root = Path(__file__).resolve().parents[3]
    exit_code = main(["--repo-root", str(repo_root)])
    assert exit_code == 0
