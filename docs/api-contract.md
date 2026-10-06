# HoneyVault REST API contract (v1) — FROZEN

> Owner: T1 lead (Nidhi) with T2 (Tanuj, Rohan). This expands `PROJECT-ROADMAP.md` §5.
> Changes only via a PR labelled `contract-change`, approved by the T1 lead and every affected
> track. T3's MSW mocks and typed client are generated from this file, so keep it exact.
> Items marked **(accepted, Phase 0)** were not specified in the brief/roadmap; they were
> proposed by the scaffold and accepted by the T1 lead. Further changes need `contract-change`.

## 0. Conventions

| Topic | Rule |
|---|---|
| Base URL | `{VITE_API_BASE_URL}/api` (local: `http://localhost:8000/api`) |
| Format | JSON (`Content-Type: application/json`), UTF-8. |
| Auth | `Authorization: Bearer <JWT>` on every route marked **JWT**. |
| IDs | User, entry and share ids are UUIDv4 strings. |
| Timestamps | ISO 8601, UTC, e.g. `"2026-10-05T14:03:22.512Z"` or `+00:00` offset. |
| OpenAPI | Served at `/docs` (Swagger UI) and `/openapi.json`; must match this file. |
| CORS | Origins from `ALLOWED_ORIGINS` (comma-separated). |

### 0.1 Error shape
Every non-2xx response has a JSON body:
```json
{"detail": "Human-readable message"}
```
- `detail` is a **string** for every error raised by application code.
- Request-body validation errors (FastAPI 422) keep FastAPI's list form,
  `{"detail": [{"loc": ["body","username"], "msg": "...", "type": "..."}]}`, **but T2 must install
  a `RequestValidationError` handler that strips the `input` (and `ctx`) fields**, because the
  default handler echoes submitted values — i.e. passwords — back into responses and logs
  (AGENTS.md §1.6). Frontend: accept `detail` as string or list.
- Error messages never contain passwords, keys, seeds or hashes.

### 0.2 Status codes used
| Code | Meaning |
|---|---|
| 200 / 201 / 204 | Success |
| 401 | Missing/invalid/expired JWT (`{"detail":"Not authenticated"}`, header `WWW-Authenticate: Bearer`), or bad login (`{"detail":"Invalid credentials"}`) |
| 403 | Authenticated but not allowed (non-admin on `/admin/*`) |
| 404 | Resource not found, or not visible to the caller, or demo endpoint while `DEMO_MODE=false` |
| 409 | Conflict (username taken) |
| 422 | Validation error (field invalid, `login_password == master_password`, …) |
| 429 | Rate limit exceeded |
| 503 | Dependency unavailable (honeychecker down → login fails closed) |

### 0.2.1 honeycore exceptions → HTTP (PROJECT-BRIEF.md §7.0)
| Exception | HTTP |
|---|---|
| `InvalidInputError` | 422 |
| `EntryNotFoundError` (unknown entry id in update/delete/export_entry_seed) | 404 `{"detail": "Entry not found"}` |
| `InvalidSignatureError` | see `POST /shares/{id}/open` (§5) |
| `WrongPasswordError` | never surfaces: raised only by the baseline vault inside the attack demo |

### 0.3 Authentication (JWT)
- Issued by `POST /auth/login`. Algorithm `JWT_ALGORITHM` (HS256), secret `JWT_SECRET`,
  lifetime `ACCESS_TOKEN_EXPIRE_MINUTES` (60).
- Claims: `sub` (user id), `username`, `is_admin`, `iat`, `exp`. **(accepted, Phase 0)**
- No refresh tokens; the SPA re-logs in on 401. Tokens are kept in memory by the SPA (not
  `localStorage`).

### 0.4 Rate limits (slowapi)
| Route | Limit (env) | Key |
|---|---|---|
| `POST /auth/login` | `RATE_LIMIT_LOGIN` = `5/minute` | client IP |
| `POST /auth/register` | `RATE_LIMIT_LOGIN` **(accepted, Phase 0)** | client IP |
| `POST /vault/unlock` | `RATE_LIMIT_UNLOCK` = `10/minute` | user id (from JWT) |

Exceeded → **429** `{"detail":"Rate limit exceeded"}` with a `Retry-After` header (seconds).
T2 must replace slowapi's default `{"error": ...}` body with this shape.

### 0.5 Field limits (PROJECT-BRIEF.md §7.1)
| Field | Rule |
|---|---|
| entry `username`, entry `password` | 1–32 printable ASCII chars (0x20–0x7E); otherwise 422 |
| entry `service` | 1–128 chars, plaintext metadata (ADR-001) **(accepted, Phase 0: 128)** |
| account `username` | 3–32 chars, `^[A-Za-z0-9_.-]+$` **(accepted, Phase 0)** |
| `login_password` | 8–128 chars **(accepted, Phase 0)** |
| `master_password` | 8–128 chars at registration; 1–128 on every other route **(accepted, Phase 0)** |

Master-password validation on unlock/add/update must depend **only on the input itself**
(length), never on whether it is correct.

---

## 1. Health

### `GET /health` — no auth
```json
200 {"status": "ok", "version": "0.1.0", "honeycore_impl": "stub", "honeychecker": "ok"}
```
`honeycore_impl`: `"stub" | "real"`. `honeychecker`: `"ok" | "down" | "unknown"` — `"unknown"`
means not checked (the Phase 0 scaffold always returns it until T2 wires the honeychecker ping).

---

## 2. Auth

### `POST /auth/register` — no auth
Request:
```json
{"username": "alice", "login_password": "Tr0ub4dor&3", "master_password": "correct horse battery staple"}
```
Server: rejects `login_password == master_password` (compared with `hmac.compare_digest`),
creates the user, k sweetwords + honeychecker registration (`/hc/register`), an empty honey vault
(`VAULT_KDF_PROFILE`), and a P-256 identity keypair + certificate (§9 of the brief).
| Status | Body |
|---|---|
| 201 | `{"id": "3f0c…", "username": "alice"}` |
| 409 | `{"detail": "Username already taken"}` |
| 422 | `{"detail": "Login password and master password must differ"}` or validation list |
| 503 | `{"detail": "Honeychecker unavailable"}` (registration cannot complete) **(accepted, Phase 0)** |

### `POST /auth/login` — no auth, rate-limited
Request: `{"username": "alice", "login_password": "Tr0ub4dor&3"}`
| Status | Body |
|---|---|
| 200 | `{"access_token": "eyJ…", "token_type": "bearer", "user": {"id": "3f0c…", "username": "alice", "is_admin": false}}` |
| 401 | `{"detail": "Invalid credentials"}` — unknown user, wrong password, **or a honeyword hit** (identical response; the honeyword case additionally creates a `HONEYWORD_LOGIN` alert) |
| 429 | rate limit |
| 503 | `{"detail": "Service temporarily unavailable"}` — honeychecker unreachable (fail closed) |

### `GET /auth/me` — JWT
```json
200 {"id": "3f0c…", "username": "alice", "is_admin": false,
     "created_at": "2026-10-05T14:03:22Z", "entry_count": 5}
```

---

## 3. Vault

> **`POST /vault/unlock` ALWAYS returns 200 for any master password.** A wrong password yields a
> complete, well-formed decoy vault with a different sigil. Status code, body shape, headers,
> timing class and log lines must not differ between right and wrong passwords
> (AGENTS.md §1.2). The only non-200 responses are 401 (JWT), 422 (malformed body — e.g. missing
> field or > 128 chars), and 429 (rate limit), all independent of password correctness.

### `POST /vault/unlock` — JWT, rate-limited
Request: `{"master_password": "correct horse battery staple"}`
```json
200 {
  "entries": [
    {"id": "9b1e…", "service": "github.com", "username": "alice@gmail.com",
     "password": "monkey123!", "created_at": "2026-10-05T14:05:00Z",
     "updated_at": "2026-10-05T14:05:00Z"}
  ],
  "sigil": {"emojis": ["🍯", "🐙", "🌊"], "color": "#F5A524"}
}
```
`entries` order = insertion order. `sigil.emojis` has exactly 3 items; `color` is `#RRGGBB`.

### `POST /vault/entries` — JWT
Request: `{"master_password": "…", "service": "github.com", "username": "alice", "password": "s3cret!"}`
| Status | Body |
|---|---|
| 201 | `{"id": "9b1e…"}` |
| 422 | field invalid (see §0.5) |

Note: a **wrong** master password still returns 201 — the entry is encrypted under that key and
will decode as noise under the real one (HE semantics, ADR-004). The UI should show the sigil
before writes so the user can spot a typo.

### `PUT /vault/entries/{id}` — JWT
Request: same body as POST. Re-encrypts only that entry.
| Status | Body |
|---|---|
| 200 | `{"id": "9b1e…"}` |
| 404 | `{"detail": "Entry not found"}` |
| 422 | field invalid |

### `DELETE /vault/entries/{id}` — JWT
`204` (no body) · `404 {"detail": "Entry not found"}`

### `GET /vault/export` — JWT
`200` the caller's vault blob v1 (PROJECT-BRIEF.md §7.8) — the "stolen file":
```json
{"format": "honeyvault", "version": 1, "scheme": "HE-PCFG-v1/AES-256-CTR/argon2id",
 "kdf": {"alg": "argon2id", "profile": "default", "salt": "<b64 16B>", "time_cost": 3,
         "memory_cost_kib": 65536, "parallelism": 4, "hash_len": 32},
 "dte": {"password_model": "pcfg-password-v1", "username_model": "pcfg-username-v1", "entry_seed_len": 532},
 "entries": [{"id": "<uuid4>", "service": "github.com", "nonce": "<b64 16B>",
              "ciphertext": "<b64 532B>", "created_at": "<ISO8601>", "updated_at": "<ISO8601>"}]}
```
With `HONEYCORE_IMPL=stub` the shape is identical but `scheme`, `kdf.alg` and the `dte` model names
carry `stub` labels.

---

## 4. Users

### `GET /users/{username}/identity` — JWT
```json
200 {"username": "bob", "public_key_pem": "-----BEGIN PUBLIC KEY-----\n…",
     "certificate_pem": "-----BEGIN CERTIFICATE-----\n…"}
```
`404 {"detail": "User not found"}`

---

## 5. Shares

### `POST /shares` — JWT
Request: `{"master_password": "…", "entry_id": "9b1e…", "recipient_username": "bob"}`
| Status | Body |
|---|---|
| 201 | `{"share_id": "c71d…"}` |
| 404 | `{"detail": "Entry not found"}` / `{"detail": "User not found"}` |
| 422 | `{"detail": "Cannot share with yourself"}` **(accepted, Phase 0)** |

A wrong master password produces a share of the decoy entry (consistent with HE; documented).

### `GET /shares/inbox` — JWT
```json
200 [{"share_id": "c71d…", "sender": "alice", "service": "github.com",
      "created_at": "2026-10-06T09:00:00Z", "opened_at": null}]
```

### `GET /shares/sent` — JWT
```json
200 [{"share_id": "c71d…", "recipient": "bob", "service": "github.com",
      "created_at": "2026-10-06T09:00:00Z", "opened_at": "2026-10-06T09:10:00Z"}]
```

### `POST /shares/{id}/open` — JWT (recipient only)
```json
200 {"service": "github.com", "username": "alice@gmail.com", "password": "monkey123!",
     "sender": "alice", "signature_valid": true, "certificate_valid": true,
     "certificate_subject": "CN=alice", "certificate_issuer": "CN=HoneyVault Issuing CA"}
```
- Sets `opened_at` on first open.
- If the signature or certificate chain/expiry check fails, the response is still 200 with the
  failing flag `false` and `username`/`password` set to `null` — nothing is decrypted.
  **(accepted, Phase 0; lets the UI render a "tampered" badge)**
- `404 {"detail": "Share not found"}` if it does not exist **or** the caller is not the recipient.

### `POST /shares/{id}/tamper` — JWT (demo mode only)
Flip one byte of the stored envelope ciphertext to simulate tampering in evaluation/demo.
Requires `DEMO_MODE=true` (otherwise 404).
| Status | Body |
|---|---|
| 200 | `{"tampered": true}` |
| 404 | `{"detail": "Share not found"}` / `{"detail": "Demo mode disabled"}` |

---

## 6. Admin

### `GET /admin/alerts` — JWT, `is_admin` required
```json
200 [{"id": "a1…", "username": "demo", "kind": "HONEYWORD_LOGIN", "severity": "critical",
      "sweetword_index": 7, "source_ip": "203.0.113.9", "user_agent": "curl/8.5",
      "created_at": "2026-10-07T18:22:10Z"}]
```
Newest first. `403 {"detail": "Admin only"}` for non-admins.

---

## 7. Evaluation

### `GET /eval/summary` — no auth
`200` the JSON contents of `EVAL_RESULTS_PATH` (`eval/results/latest.json`; schema defined by T1
in Phase 2). `404 {"detail": "No evaluation results yet"}` if the file does not exist.

---

## 8. Attack demo (only when `DEMO_MODE=true`; otherwise every route → 404)
No JWT: the attacker console is public in demo deployments. All data comes from the seeded
`DEMO_USERNAME` account and uses the `demo` KDF profile.

### `GET /attack/stolen-vault`
```json
200 {"honey_blob": {/* vault blob v1 */}, "baseline_blob": {/* conventional vault dict */}, "owner": "demo"}
```

### `POST /attack/dictionary`
Request: `{"max_guesses": 500, "custom_guesses": ["password1", "dragon"]}`
(`max_guesses` 1–2000; `custom_guesses` optional, ≤ 2000 items, each 1–128 chars, tried first.)
```json
200 {
  "baseline": {"cracked": true, "guess_index": 137, "elapsed_ms": 812,
               "recovered_entries": [{"id": "…", "service": "github.com", "username": "…",
                                      "password": "…", "created_at": "…", "updated_at": "…"}]},
  "honey": {"guesses_tried": 500, "elapsed_ms": 1904, "distinct_vaults": 500,
            "samples": [{"guess_index": 0, "guess": "123456",
                         "entries": [{"id": "…", "service": "github.com", "username": "…",
                                      "password": "…", "created_at": "…", "updated_at": "…"}]}]},
  "reveal": {"real_guess_index": 137}
}
```
`samples` ≤ 25. If the real password is not in the list: `baseline.cracked=false`,
`baseline.guess_index=null`, `recovered_entries=[]`, `reveal.real_guess_index=null`.
`422` if `max_guesses` out of range.

### `GET /attack/stolen-honeywords`
```json
200 {"username": "demo", "k": 10, "salt": "<b64>", "hashes": ["<b64>", "… k items"],
     "cracked_sweetwords": ["summer2019!", "… k items, same order as hashes"]}
```

### `GET /attack/alarms`
Recent alerts for the demo user, same item shape as `/admin/alerts`, newest first (≤ 20).

---

## 9. Utilities (optional, T5)

### `POST /utils/strength` — no auth
Request: `{"password": "monkey123"}`
```json
200 {"score": 1, "entropy_bits": 28.4, "feedback": ["Common word + digits", "Add length"]}
```
`score` 0–4. Route is absent (404) if `app/api/utils.py` is not installed; the frontend falls back
to its client-side meter.

---

## 10. Honeychecker internal API (service-to-service only)

Base: `HONEYCHECKER_URL` (local `http://localhost:8001`). Never exposed to the browser; no CORS.

**Caller authentication** per `HONEYCHECKER_TRANSPORT` / `HC_TRANSPORT` (must match):
| Mode | How |
|---|---|
| `plain` | none — local development only |
| `mtls` | TLS client cert issued by our Issuing CA; server checks CN == `HC_ALLOWED_CLIENT_CN` (`honeyvault-api`) |
| `signed` | headers `X-HV-Cert` (b64 PEM client cert), `X-HV-Timestamp` (unix seconds), `X-HV-Nonce` (random, b64/hex), `X-HV-Signature` (b64 DER ECDSA-P256-SHA256 over `METHOD\nPATH\nTS\nNONCE\nhex(SHA256(body))`); server verifies chain → Root, CN, EKU clientAuth, \|now − ts\| ≤ 60 s, nonce unused in last 5 min |

Auth failure → `401 {"detail": "Unauthorized"}`. `/hc/health` is unauthenticated.

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/hc/health` | – | `200 {"status": "ok", "service": "honeychecker", "version": "0.1.0"}` |
| POST | `/hc/register` | `{"user_id": "3f0c…", "index": 4}` | `201 {"status": "registered"}`; `409 {"detail": "Already registered"}`; `422` if `index` < 0 |
| POST | `/hc/check` | `{"user_id": "3f0c…", "index": 7}` | `200 {"match": false}` (a mismatch is logged as an alarm); `404 {"detail": "Unknown user"}` |
| GET | `/hc/alarms` | – | `200 [{"id": 1, "user_id": "3f0c…", "submitted_index": 7, "created_at": "…"}]` newest first |

API behaviour: any honeychecker error, timeout (`HONEYCHECKER_TIMEOUT_SECONDS`) or non-2xx during
login → `503` to the client (fail closed). The API never stores the real index.
