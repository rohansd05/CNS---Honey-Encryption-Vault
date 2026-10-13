# AGENTS.md — Rules for AI coding agents (Claude Code, Antigravity, etc.)

You are contributing to **HoneyVault**, a Honey Encryption password vault built by team
Ocean's 10 for SPIT's CNS course (ACNS-DC 2026-27).

**Before writing any code, read `PROJECT-BRIEF.md` (what & why, normative crypto spec)
and `PROJECT-ROADMAP.md` (who owns what, current phase, contracts).**

## 1. Crypto invariants — NEVER violate (these are the whole point of the project)
1. The honey-vault ciphertext must have **no MAC, no auth tag, no padding, no checksum, no magic
   bytes, no version byte inside the encrypted part, and no stored hash of the master password
   or of the derived key**. Any of these recreates the offline "correct password?" oracle.
2. `HoneyVault.unlock()` and `/api/vault/unlock` must **never raise, error, or behave differently**
   (status code, response shape, timing class, log line) for a wrong master password. Always return
   a full, well-formed vault.
3. `DTE.decode()` must be **total**: every byte string of the right length decodes to a valid,
   printable value. Any exception there is a bug.
4. Seeds are **fixed-length** (`ENTRY_SEED_LEN`). Never make ciphertext length depend on content.
5. Randomness: use `secrets` / `os.urandom` only. Never `random` in `honeycore/` or `app/`.
6. Never log, print, store or return in errors: master passwords, login passwords, derived keys,
   seeds, private keys. Redact in exceptions.
7. Login password ≠ master password (enforced at registration). Never derive anything verifiable
   from the master password and store it.
8. Use `hmac.compare_digest` for all secret comparisons.
9. AES-GCM is allowed ONLY for: the conventional baseline vault, share envelopes, and key wrapping
   with the server KEK — never for honey-vault entries.
10. Never commit secrets, `.env`, keys/certs (`pki/out/`), raw corpora (`data/`) or `*.db`.

## 2. Ownership — stay in your lane
Each track owns specific paths (see PROJECT-ROADMAP.md §2). Only edit files your track owns.
If you need a change elsewhere, write it up as a note for the owning track instead of editing.
**Frozen contracts** — change only via a PR labelled `contract-change`, approved by the T1 lead:
- `backend/honeycore/interfaces.py`
- `docs/api-contract.md`
- the vault blob format and env var names (PROJECT-BRIEF.md §7, `.env.example`)
Until a real implementation lands, code against `honeycore/stubs.py` (`HONEYCORE_IMPL=stub`)
or frontend MSW mocks (`VITE_USE_MOCKS=true`). Never block on another track.

## 3. Tech & style
- **Python 3.12**, type hints everywhere, `ruff` clean (config in `backend/pyproject.toml`),
  docstrings on public functions. FastAPI routers + Pydantic v2 schemas; SQLAlchemy 2.0 style;
  Alembic for every schema change.
- `honeycore/` is a pure library: no FastAPI/SQLAlchemy imports, no I/O except loading model files.
- **Frontend**: React + TypeScript (strict) + Vite + Tailwind + shadcn/ui, TanStack Query for
  server state, react-hook-form + zod for forms, lucide-react icons, sonner toasts, recharts for
  charts. API calls only via `src/api/` client. No `any`. No localStorage for secrets — the
  master password lives only in component state and is cleared on lock/logout.
- Tests: `pytest` (+ `hypothesis` for DTE/vault properties). Frontend: `npm run lint && npm run build`.

## 4. Commands
```bash
# backend (from backend/, venv active)
ruff check . && ruff format --check .
pytest
uvicorn app.main:app --reload --port 8000
# honeychecker (from honeychecker/, same venv)
uvicorn app.main:app --reload --port 8001
# frontend (from frontend/)
npm install && npm run dev      # http://localhost:5173
npm run lint && npm run build
```

## 5. Git workflow — HUMANS ONLY
**AI agents MUST NEVER run any git/GitHub command that changes state** — no `git add`, `commit`,
`push`, `pull`, `merge`, `rebase`, `reset`, `restore`, `checkout`, `switch`, `stash`, `tag`,
`cherry-pick`, `revert`, `clean`, `rm`, `mv`, `remote`, and no `gh pr` / `gh repo` / `gh release`.
Allowed (read-only): `git status`, `git diff`, `git log`, `git show`, `git branch --show-current`.
Agents only edit files. Humans review `git diff` and run the commit/push commands given by the T1 lead.
End every session by printing `git status --short` and a suggested commit message.

- Repo: https://github.com/rohansd05/CNS---Honey-Encryption-Vault (admin: Rohan, @rohansd05).
- Branch from `dev`: `feat/t<N>-<desc>`, e.g. `feat/t1-pcfg-trainer`, `fix/t2-login-rate-limit`.
- Conventional commits: `feat(dte): ...`, `fix(api): ...`, `test(vault): ...`, `docs: ...`, `chore: ...`.
- Small PRs into `dev`; ≥1 approval from a CODEOWNER; CI green.
- Each person commits from their own GitHub account on files they own. Pair-programmed commits add
  `Co-authored-by: Name <github-email>`.
- `dev` → `main` only at phase ends (T1 lead + Vedant).

## 6. Definition of done (every task)
- [ ] Code + tests in the owning track's paths; `ruff`/`pytest` or `lint`/`build` pass locally.
- [ ] No crypto invariant (§1) violated; no secrets in code, logs, or fixtures.
- [ ] Public functions documented; docs/ updated if behaviour or API changed.
- [ ] At the end of your session, print: files changed, commands run + results, deviations
      from the brief/contract, and open TODOs for other tracks.