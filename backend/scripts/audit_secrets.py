"""Secret and insecure logging auditor for HoneyVault.

Audits repository git history and working tree for:
1. Leaked private keys (PEM and Base64-encoded -----BEGIN markers).
2. Committed sensitive files (.env, *.key, *.pem, *.p12).
3. PostgreSQL connection URLs containing passwords.
4. Hardcoded JWT_SECRET and KEY_WRAP_SECRET assignments.
5. Insecure logging/print calls in backend/ and honeychecker/ mentioning sensitive terms.

Output format:
    check | findings | PASS/FAIL
"""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# =============================================================================
# ALLOWLIST
# Small, explicit, documented allowlist for safe placeholders, mock fixtures,
# documentation examples, and self-inspection.
# =============================================================================


@dataclass(frozen=True)
class AllowlistRule:
    """Explicitly justified allowlist exclusion."""

    rule: str
    file: str
    reason: str
    line: int | None = None
    commit: str | None = None


ALLOWLIST_RULES: tuple[AllowlistRule, ...] = (
    # Self-exclusion: Auditor script and test suite define and test detection patterns
    AllowlistRule(
        rule="*",
        file="backend/scripts/audit_secrets.py",
        reason="Auditor script source code defines detection patterns and regexes.",
    ),
    AllowlistRule(
        rule="*",
        file="backend/tests/infra/test_audit_secrets.py",
        reason="Auditor test suite contains synthetic test fixtures.",
    ),
    # Documentation examples: Canonical AWS documentation example Access Key ID
    AllowlistRule(
        rule="cloud-token",
        file="frontend/src/mocks/handlers/vault.ts",
        line=35,
        reason=(
            "Documentation example: Canonical AWS documentation example Access Key ID "
            "used in mock entries."
        ),
    ),
    # Safe mock placeholders: Mock Service Worker fake session JWT tokens
    AllowlistRule(
        rule="hardcoded-secret",
        file="frontend/src/mocks/handlers/auth.ts",
        line=36,
        reason=(
            "Safe mock placeholder: Mock Service Worker demo session token (mock-jwt-token-demo)."
        ),
    ),
    AllowlistRule(
        rule="hardcoded-secret",
        file="frontend/src/mocks/handlers/auth.ts",
        line=44,
        reason=(
            "Safe mock placeholder: Mock Service Worker admin session token (mock-jwt-token-admin)."
        ),
    ),
    # CLI setup display: Local demo seeder outputs one-time ephemeral admin master password
    AllowlistRule(
        rule="sensitive-logging",
        file="backend/scripts/seed_demo.py",
        line=116,
        reason=(
            "CLI setup display: Local demo seeder outputs one-time ephemeral admin master password "
            "to console for developer login."
        ),
    ),
)


# Markers and patterns assembled at runtime so self-scanning does not trip itself.
_PEM_PREFIX = "-----" + "BEGIN"
_PEM_SUFFIX = "PRIVATE" + " KEY-----"
PEM_KEY_REGEX = re.compile(re.escape(_PEM_PREFIX) + r"(?: [A-Z0-9_\-]+)* " + re.escape(_PEM_SUFFIX))

_B64_PREFIX = "LS0tLS1C" + "RUdJTi"
BASE64_PEM_REGEX = re.compile(re.escape(_B64_PREFIX))

AWS_KEY_REGEX = re.compile(r"\b(?:AKIA|ASIA|AROA|AIPA)[0-9A-Z]{16}\b")
GITHUB_TOKEN_REGEX = re.compile(
    r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{82}\b"
)
SLACK_TOKEN_REGEX = re.compile(r"\bxox[baprs]-[0-9A-Za-z]{10,48}\b")

# Sensitive variable assignments: JWT_SECRET and KEY_WRAP_SECRET
_SECRET_ASSIGN_VARS = (
    "jwt_" + "secret",
    "key_wrap_" + "secret",
)
SENSITIVE_ASSIGN_REGEX = re.compile(
    r"(?i)\b(?:"
    + "|".join(re.escape(v) for v in _SECRET_ASSIGN_VARS)
    + r")\s*[:=]\s*['\"]?([A-Za-z0-9_\-\./+=]{16,})['\"]?"
)

# PostgreSQL connection URI containing password
DB_URI_REGEX = re.compile(r"\b(?:postgres|postgresql)://([^:]+):([^@\s/]+)@")

# Sensitive terms for AST logging checks: password, master, sweetword, seed, key_wrap
_SENSITIVE_LOG_PARTS = (
    ("pass", "word"),
    ("mas", "ter"),
    ("sweet", "word"),
    ("se", "ed"),
    ("key_", "wrap"),
)
SENSITIVE_LOG_TERMS = tuple(p1 + p2 for p1, p2 in _SENSITIVE_LOG_PARTS)

# Sensitive file extensions and committed environment files
SENSITIVE_FILE_EXTENSIONS = frozenset({".key", ".pem", ".p12"})

_DUMMY_SECRET_INDICATORS = (
    "change",
    "dummy",
    "example",
    "placeholder",
    "test",
    "xxxx",
    "<",
    ">",
    "your-",
    "mock-",
)

_DUMMY_DB_PASSWORDS = frozenset(
    {
        "password",
        "postgres",
        "user",
        "root",
        "change-me",
        "xxxx",
        "<password>",
        "PASSWORD",
    }
)

BINARY_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".svg",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".pyc",
        ".tar",
        ".gz",
        ".bz2",
        ".zip",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
    }
)


@dataclass(frozen=True)
class Finding:
    """Represents an audit finding.

    Never stores matched secret text or line contents to prevent leaking secrets.
    """

    rule: str
    file: str
    line: int
    commit: str | None = None

    def __str__(self) -> str:
        if self.commit:
            return f"[{self.rule}] {self.file}:{self.line} (commit: {self.commit})"
        return f"[{self.rule}] {self.file}:{self.line}"


def is_allowlisted_path(path: str | Path) -> bool:
    """Return True if path is allowlisted from full file-level scanning."""
    normalized = str(path).replace("\\", "/").lstrip("./")
    for rule in ALLOWLIST_RULES:
        if rule.rule == "*":
            target = rule.file.replace("\\", "/").lstrip("./")
            if normalized == target or normalized.endswith(target):
                return True
    return False


def is_allowlisted_finding(finding: Finding) -> bool:
    """Return True if a finding matches a documented allowlist rule."""
    norm_file = finding.file.replace("\\", "/").lstrip("./")
    for rule in ALLOWLIST_RULES:
        if rule.rule != "*" and rule.rule != finding.rule:
            continue
        rule_norm = rule.file.replace("\\", "/").lstrip("./")
        if norm_file != rule_norm and not norm_file.endswith(rule_norm):
            continue
        if rule.line is not None and rule.line != finding.line:
            continue
        if rule.commit is not None and rule.commit != finding.commit:
            continue
        return True
    return False


def is_sensitive_file_path(path_str: str) -> bool:
    """Check if file path is a sensitive file like .env or private key/certificate."""
    p = Path(path_str)
    name_lower = p.name.lower()

    # Detect committed .env files (except .env.example)
    if name_lower == ".env" or (name_lower.startswith(".env.") and name_lower != ".env.example"):
        return True

    # Detect sensitive extensions (.key, .pem, .p12)
    if p.suffix.lower() in SENSITIVE_FILE_EXTENSIONS:
        return True

    return False


def scan_line_for_secrets(
    content: str,
    file_path: str,
    line_no: int,
    commit: str | None = None,
) -> list[Finding]:
    """Scan a single line of text for secret patterns.

    Omit matched text from findings.
    """
    findings: list[Finding] = []

    # 1. Private key markers (PEM and Base64-encoded -----BEGIN)
    if PEM_KEY_REGEX.search(content) or BASE64_PEM_REGEX.search(content):
        findings.append(Finding(rule="private-key", file=file_path, line=line_no, commit=commit))

    # 2. Cloud and API tokens
    if (
        AWS_KEY_REGEX.search(content)
        or GITHUB_TOKEN_REGEX.search(content)
        or SLACK_TOKEN_REGEX.search(content)
    ):
        findings.append(Finding(rule="cloud-token", file=file_path, line=line_no, commit=commit))

    # 3. Hardcoded secret variable assignment (JWT_SECRET, KEY_WRAP_SECRET)
    assign_match = SENSITIVE_ASSIGN_REGEX.search(content)
    if assign_match:
        val = assign_match.group(1).lower()
        if not any(indicator in val for indicator in _DUMMY_SECRET_INDICATORS):
            findings.append(
                Finding(rule="hardcoded-secret", file=file_path, line=line_no, commit=commit)
            )

    # 4. Database password in PostgreSQL URI
    db_match = DB_URI_REGEX.search(content)
    if db_match:
        user = db_match.group(1)
        pw = db_match.group(2)
        if (
            pw not in _DUMMY_DB_PASSWORDS
            and not (user == "USER" and pw == "PASSWORD")
            and not any(d in pw.lower() for d in _DUMMY_SECRET_INDICATORS)
        ):
            findings.append(
                Finding(rule="database-password", file=file_path, line=line_no, commit=commit)
            )

    return findings


def is_plain_string_literal(node: ast.AST) -> bool:
    """Return True if node represents exclusively a plain string literal."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return is_plain_string_literal(node.left) and is_plain_string_literal(node.right)
    return False


def _contains_sensitive_term(identifier: str) -> bool:
    """Return True if identifier contains any sensitive logging term.

    Ignores harmless metadata identifiers like *_index, *_idx, *_count, *_len.
    """
    lower = identifier.lower()
    non_secret_suffixes = ("_index", "_idx", "_count", "_len", "_length")
    if any(lower.endswith(sfx) for sfx in non_secret_suffixes):
        return False
    return any(term in lower for term in SENSITIVE_LOG_TERMS)


def inspect_expression_for_sensitive(node: ast.AST) -> bool:
    """Inspect an argument expression for sensitive terms.

    Flag only when a sensitive term appears in a variable name, f-string expression
    or argument, NOT when it is only part of a plain string literal message.
    """
    if is_plain_string_literal(node):
        return False

    # Ignore metadata function calls like len(sweetwords) which output integer counts
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in ("len", "bool")
    ):
        return False

    if isinstance(node, ast.JoinedStr):
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                if inspect_expression_for_sensitive(part.value):
                    return True
        return False

    for child in ast.walk(node):
        # Skip arguments to metadata length/bool calls
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id in ("len", "bool")
        ):
            continue
        if isinstance(child, ast.Name) and _contains_sensitive_term(child.id):
            return True
        if isinstance(child, ast.Attribute) and _contains_sensitive_term(child.attr):
            return True
        if isinstance(child, ast.keyword) and child.arg and _contains_sensitive_term(child.arg):
            return True
        if isinstance(child, ast.Dict):
            for k in child.keys:
                if k is not None and isinstance(k, ast.Constant) and isinstance(k.value, str):
                    if _contains_sensitive_term(k.value):
                        return True
        if isinstance(child, ast.Subscript):
            slice_node = child.slice
            if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                if _contains_sensitive_term(slice_node.value):
                    return True
        if isinstance(child, ast.JoinedStr):
            for part in child.values:
                if isinstance(part, ast.FormattedValue):
                    if inspect_expression_for_sensitive(part.value):
                        return True

    return False


def is_logging_call(node: ast.Call) -> bool:
    """Return True if Call node is a print(), logging.*, or logger.* call."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "print":
        return True

    if isinstance(func, ast.Attribute):
        method_name = func.attr
        logging_methods = {
            "debug",
            "info",
            "warning",
            "warn",
            "error",
            "critical",
            "fatal",
            "exception",
            "log",
        }
        if method_name in logging_methods:
            val = func.value
            if isinstance(val, ast.Name) and val.id.lower() in (
                "logging",
                "logger",
                "_logger",
                "log",
            ):
                return True
            if isinstance(val, ast.Attribute) and val.attr.lower() in (
                "logger",
                "_logger",
                "log",
                "logging",
            ):
                return True
            if isinstance(val, ast.Call):
                call_func = val.func
                if isinstance(call_func, ast.Attribute) and call_func.attr == "getLogger":
                    return True

    return False


class LoggingLeakVisitor(ast.NodeVisitor):
    """AST visitor detecting logging or print calls leaking sensitive variables."""

    def __init__(self, file_path: str, commit: str | None = None) -> None:
        self.file_path = file_path
        self.commit = commit
        self.findings: list[Finding] = []

    def visit_Call(self, node: ast.Call) -> None:
        if is_logging_call(node):
            flagged = False
            for arg in node.args:
                if inspect_expression_for_sensitive(arg):
                    flagged = True
                    break
            if not flagged:
                for kw in node.keywords:
                    if kw.arg and _contains_sensitive_term(kw.arg):
                        flagged = True
                        break
                    if inspect_expression_for_sensitive(kw.value):
                        flagged = True
                        break
            if flagged:
                self.findings.append(
                    Finding(
                        rule="sensitive-logging",
                        file=self.file_path,
                        line=node.lineno,
                        commit=self.commit,
                    )
                )

        self.generic_visit(node)


def scan_python_code_ast(
    code: str,
    file_path: str,
    commit: str | None = None,
    line_offset: int = 0,
) -> list[Finding]:
    """Parse Python code with ast and detect insecure logging calls."""
    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError:
        return []

    visitor = LoggingLeakVisitor(file_path=file_path, commit=commit)
    visitor.visit(tree)

    if line_offset == 0:
        return visitor.findings

    adjusted: list[Finding] = []
    for f in visitor.findings:
        adjusted.append(
            Finding(
                rule=f.rule,
                file=f.file,
                line=f.line + line_offset,
                commit=f.commit,
            )
        )
    return adjusted


def scan_git_history(
    repo_path: Path | str,
    timeout: float = 60.0,
    commit_range: str | None = None,
) -> Iterator[Finding]:
    """Scan git history for secrets, streaming output line by line.

    Runs git log -p --all with UTF-8 encoding and timeout.
    Only inspects added lines (starting with '+', not '+++').
    """
    repo = Path(repo_path)
    git_bin = shutil.which("git") or "git"
    cmd = [git_bin, "log", "-p", "--all", "--full-history"]
    if commit_range:
        cmd.append(commit_range)

    start_time = time.monotonic()
    process = subprocess.Popen(  # noqa: S603
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=repo,
        bufsize=1,
    )

    current_commit: str | None = None
    current_file: str | None = None
    current_line_no = 0

    try:
        if process.stdout is None:
            return

        for raw_line in process.stdout:
            if time.monotonic() - start_time > timeout:
                process.kill()
                process.wait()
                raise TimeoutError(f"Git history audit timed out after {timeout} seconds")

            line = raw_line.rstrip("\r\n")

            if line.startswith("commit "):
                parts = line.split()
                if len(parts) >= 2:
                    current_commit = parts[1]
                current_file = None
                current_line_no = 0
                continue

            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                if current_file and is_sensitive_file_path(current_file):
                    yield Finding(
                        rule="committed-files",
                        file=current_file,
                        line=1,
                        commit=current_commit,
                    )
                continue

            if line.startswith("+++ /dev/null"):
                current_file = None
                continue

            # Parse hunk header: @@ -old,len +new,len @@
            if line.startswith("@@ "):
                m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if m:
                    current_line_no = int(m.group(1))
                continue

            # Only inspect added lines (starting with '+', not '+++')
            if line.startswith("+") and not line.startswith("+++"):
                added_content = line[1:]
                line_no = current_line_no
                current_line_no += 1

                if current_file and current_commit:
                    for finding in scan_line_for_secrets(
                        content=added_content,
                        file_path=current_file,
                        line_no=line_no,
                        commit=current_commit,
                    ):
                        yield finding

                    # Check added Python statements with AST for insecure logging
                    if current_file.endswith(".py"):
                        stripped = added_content.strip()
                        if stripped and any(k in stripped for k in ("print", "log", "Log")):
                            for finding in scan_python_code_ast(
                                code=stripped,
                                file_path=current_file,
                                commit=current_commit,
                                line_offset=line_no - 1,
                            ):
                                yield finding

            elif line.startswith("-") and not line.startswith("---"):
                pass
            else:
                if current_line_no > 0:
                    current_line_no += 1

        if time.monotonic() - start_time > timeout:
            raise TimeoutError(f"Git history audit timed out after {timeout} seconds")

    finally:
        if process.stdout:
            process.stdout.close()
        try:
            remaining = max(0.1, timeout - (time.monotonic() - start_time))
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def find_repo_root(start_dir: Path | None = None) -> Path:
    """Find repository root by searching upward for .git directory."""
    curr = (start_dir or Path(__file__)).resolve()
    if curr.is_file():
        curr = curr.parent

    for p in [curr, *curr.parents]:
        if (p / ".git").is_dir():
            return p
    return Path.cwd().resolve()


def get_working_tree_files(repo_root: Path) -> list[Path]:
    """Retrieve list of tracked files in the working tree."""
    git_bin = shutil.which("git") or "git"
    try:
        res = subprocess.run(  # noqa: S603
            [git_bin, "ls-files"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        files: list[Path] = []
        for rel in res.stdout.splitlines():
            rel_str = rel.strip()
            if rel_str:
                p = repo_root / rel_str
                if p.is_file():
                    files.append(p)
        return files
    except (subprocess.SubprocessError, FileNotFoundError):
        files = []
        for p in repo_root.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                files.append(p)
        return files


def scan_committed_files(repo_root: Path) -> list[Finding]:
    """Check for committed .env files or sensitive key/pem/p12 files."""
    findings: list[Finding] = []
    files = get_working_tree_files(repo_root)
    for file_path in files:
        try:
            rel_path = file_path.relative_to(repo_root).as_posix()
        except ValueError:
            rel_path = file_path.as_posix()

        if is_sensitive_file_path(rel_path):
            findings.append(Finding(rule="committed-files", file=rel_path, line=1))

    return findings


def scan_sensitive_logging(repo_root: Path) -> list[Finding]:
    """Scan backend/ and honeychecker/ for logging and print calls leaking secrets."""
    findings: list[Finding] = []
    files = get_working_tree_files(repo_root)

    for p in files:
        if p.suffix.lower() != ".py":
            continue
        try:
            rel = p.relative_to(repo_root).as_posix()
        except ValueError:
            rel = p.as_posix()

        # Only scan backend/ and honeychecker/
        if not (rel.startswith("backend/") or rel.startswith("honeychecker/")):
            continue

        if is_allowlisted_path(rel):
            continue

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        findings.extend(scan_python_code_ast(content, file_path=rel))

    return findings


def scan_working_tree(repo_root: Path) -> list[Finding]:
    """Scan working-tree files for secret markers and sensitive assignments."""
    findings: list[Finding] = []
    files = get_working_tree_files(repo_root)

    for file_path in files:
        try:
            rel_path = file_path.relative_to(repo_root).as_posix()
        except ValueError:
            rel_path = file_path.as_posix()

        if is_allowlisted_path(rel_path):
            continue

        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for idx, line in enumerate(content.splitlines(), start=1):
            findings.extend(
                scan_line_for_secrets(content=line, file_path=rel_path, line_no=idx, commit=None)
            )

    return findings


def format_table(results: dict[str, tuple[int, bool]]) -> str:
    """Format check results as required table: check | findings | PASS/FAIL."""
    header = f"{'check':<25} | {'findings':<8} | {'PASS/FAIL'}"
    separator = f"{'-' * 25}-+-{'-' * 8}-+-{'-' * 9}"
    lines = [header, separator]
    for check_name, (count, passed) in results.items():
        status = "PASS" if passed else "FAIL"
        lines.append(f"{check_name:<25} | {count:<8} | {status}")
    return "\n".join(lines)


def run_audit(
    repo_root: Path,
    timeout: float = 60.0,
) -> tuple[dict[str, tuple[int, bool]], list[Finding]]:
    """Execute all required audit checks and return summary and unapproved findings."""
    results: dict[str, tuple[int, bool]] = {}
    all_unapproved: list[Finding] = []

    # 1. Committed sensitive files check
    comm_findings = [f for f in scan_committed_files(repo_root) if not is_allowlisted_finding(f)]
    results["committed-files"] = (len(comm_findings), len(comm_findings) == 0)
    all_unapproved.extend(comm_findings)

    # 2. Sensitive logging check in backend/ and honeychecker/
    log_findings = [f for f in scan_sensitive_logging(repo_root) if not is_allowlisted_finding(f)]
    results["sensitive-logging"] = (len(log_findings), len(log_findings) == 0)
    all_unapproved.extend(log_findings)

    # 3. Working tree secret scan
    wt_findings = [f for f in scan_working_tree(repo_root) if not is_allowlisted_finding(f)]
    results["working-tree"] = (len(wt_findings), len(wt_findings) == 0)
    all_unapproved.extend(wt_findings)

    # 4. Git history streaming scan
    git_findings: list[Finding] = []
    try:
        for f in scan_git_history(repo_root, timeout=timeout):
            if not is_allowlisted_finding(f):
                git_findings.append(f)
        results["git-history"] = (len(git_findings), len(git_findings) == 0)
        all_unapproved.extend(git_findings)
    except Exception as err:
        # Never dump secret-bearing Git output; record scan failure safely
        print(f"Error executing git history audit: {type(err).__name__}", file=sys.stderr)
        results["git-history"] = (len(git_findings) + 1, False)

    return results, all_unapproved


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for secret and logging auditor."""
    parser = argparse.ArgumentParser(
        description="Audit repository for leaked secrets and insecure logging.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Path to repository root (defaults to auto-detecting git root).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Timeout in seconds for git history streaming.",
    )

    args = parser.parse_args(argv)
    repo_root = find_repo_root(args.repo_root)

    results, unapproved_findings = run_audit(repo_root, timeout=args.timeout)

    print()
    print(format_table(results))
    print()

    if unapproved_findings:
        print("Unapproved findings:")
        print("-" * 50)
        sorted_findings = sorted(
            unapproved_findings,
            key=lambda x: (x.rule, x.file, x.line, x.commit or ""),
        )
        for f in sorted_findings:
            print(f)
        print("-" * 50)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
