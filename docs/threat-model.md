# Threat model

> Owner: T1 lead (Nidhi), with T4 (Parth) for the network/PKI parts. Source: PROJECT-BRIEF.md §12.

## Assets
- Vault entries (usernames/passwords) of every user.
- Users' master passwords (never stored) and login passwords (stored only as k sweetword hashes).
- Identity private keys (wrapped with the server KEK `KEY_WRAP_SECRET`).
- The honeychecker's `user_id → real index` table.
- Root CA key (offline, `pki/out/`, never deployed) and Issuing CA key (`ISSUING_CA_KEY_B64`).

## Attackers
| Id | Capability | Goals | Defences |
|---|---|---|---|
| **A1** offline thief | Steals the API database: vault blobs, honeyword hashes, shares | Recover entries; confirm a master password guess offline | **Honey Encryption**: no MAC/checksum/key hash, so every guess decrypts to a plausible vault — there is no oracle. **Honeywords**: cracking the k hashes yields k candidates; logging in with a decoy raises a `HONEYWORD_LOGIN` alarm via the separate honeychecker. Argon2id slows every guess. |
| **A2** online attacker | Talks to the public API | Guess login passwords; enumerate users; abuse demo endpoints | Rate limits (`RATE_LIMIT_LOGIN`, `RATE_LIMIT_UNLOCK`), JWT on every private route, generic errors (`Invalid credentials` for every login failure, including honeyword hits), `DEMO_MODE` off in production. |
| **A3** network attacker (between API and honeychecker) | Observes/modifies service traffic | Forge `/hc/check` answers, replay requests | mTLS (compose) or ECDSA-signed requests with timestamp + nonce replay cache (Render), certificates from our own CA (ADR-005). |
| **A4** malicious share sender/MITM | Alters an envelope or impersonates a sender | Make a recipient accept forged data | ECDSA signature over the envelope, sender certificate chain to our Root CA, AES-GCM AEAD with bound `aad`. |

## Out of scope
- Full server compromise (the KEK lives in env; an attacker with code execution sees plaintext
  as users unlock).
- Client-side malware / keyloggers.
- Multi-snapshot correlation (comparing vault blobs stolen at different times reveals which entry
  changed).
- Traffic analysis; ciphertext length reveals the number of entries.

## Invariants (AGENTS.md §1)
1. No MAC, tag, padding, checksum, magic bytes or stored key/password hash in honey ciphertext.
2. `unlock` / `/api/vault/unlock` never errors or behaves differently for a wrong password.
3. `DTE.decode` is total.
4. Seeds are fixed length (`ENTRY_SEED_LEN` = 532 B).
5. Randomness only from `secrets` / `os.urandom`.
6. Never log/return passwords, keys, seeds, private keys.
7. Login password ≠ master password; nothing verifiable is derived from the master password.
8. `hmac.compare_digest` for all secret comparisons.
9. AES-GCM only for the baseline vault, share envelopes and KEK wrapping.
10. No secrets, keys, corpora or databases in git.

## Known residual risks
- A user who mistypes their master password while **adding** an entry stores it under the wrong
  key (it decodes as noise later). Mitigation: Sigil shown before writes (ADR-004).
- Decoy quality depends on the PCFG; an ML distinguisher may beat 50% (we report it honestly).
- Decoy entries are independent, so password reuse in a real vault is a distinguishing signal
  (stretch goal in Phase 3).

---

## Service trust domains and the two-CA hierarchy

> Source: `pki/README.md`, `honeychecker/app/security.py`.

HoneyVault operates **two completely separate X.509 CA hierarchies** with distinct trust stores.

### User-identity hierarchy (Root → Issuing CA → user cert)

| CA / Cert | Key | Validity | Purpose |
|-----------|-----|----------|---------|
| **Root CA** (`root_ca.crt`) | P-256 | 10 yr | Offline trust anchor; key never deployed |
| **Issuing CA** (`issuing_ca.crt`) | P-256 | 5 yr | Issues user identity certs in-app |
| **User cert** (CN = username) | P-256 | 1 yr | ECDSA for secure entry sharing (§9) |

### Service hierarchy (Service CA → service leaf certs)

| CA / Cert | Key | Validity | Purpose |
|-----------|-----|----------|---------|
| **Service CA** (`service-ca.crt`) | P-256 | 10 yr | Trust anchor for the API↔honeychecker channel; key offline |
| **honeychecker-server** | P-256 | 1 yr | uvicorn TLS server cert (SAN: `localhost`, `honeychecker`) |
| **api-client** | P-256 | 1 yr | mTLS / signed-request client cert (EKU `clientAuth`) |

### Why a user cert can never reach the honeychecker

The honeychecker's trust store (`HC_TRUSTED_CA_CERT_B64`) contains **only the Service CA**.
The user-identity Root CA is **never** placed in the honeychecker's config
(`pki/README.md` §Why Two Separate CAs).

**Cryptographic consequence:** A user identity certificate — whether legitimately issued
(Root → Issuing CA → username) or forged under a compromised Issuing CA — cannot build a valid
chain to the Service CA. `verify_signed_request` in `backend/honeycore/transport.py` calls
`PKI.verify_certificate(cert_pem, trusted_ca_pems, expected_cn=allowed_cn, require_client_auth=True)`,
where `trusted_ca_pems` is loaded exclusively from `HC_TRUSTED_CA_CERT_B64` /
`HC_TRUSTED_CA_CERT_PATH` (`honeychecker/app/security.py` → `_load_trusted_ca_pems`).

Without this separation, a user cert with `CN=honeyvault-api` (the value of `HC_ALLOWED_CLIENT_CN`)
could impersonate the API to the honeychecker, silently converting a decoy login into a non-alarm —
the worst-case failure of the honeyword system.

---

## Transport security per environment

> Source: `docs/decisions/ADR-005.md`, `backend/honeycore/transport.py`,
> `honeychecker/app/security.py`.

The environment variable pair `HONEYCHECKER_TRANSPORT` (API side) / `HC_TRANSPORT`
(honeychecker side) selects one of three modes. Both must agree.

### Mode matrix

| Mode | Environment | TLS layer | Application-layer auth | What it defends against |
|------|-------------|-----------|------------------------|------------------------|
| `plain` | **Local dev only** | None (HTTP) | None | Nothing — no security |
| `mtls` | **Docker-compose** | Mutual TLS (uvicorn `--ssl-cert-reqs CERT_REQUIRED`, `--ssl-ca-certs` = Service CA) | CN check on peer cert when ASGI scope exposes it (defence-in-depth) | Network sniffer on the compose bridge; forged responses from a non-CA-issued cert |
| `signed` | **Render (staging/prod)** | TLS terminated at Render's proxy; HTTPS end-to-end to client | ECDSA-P256-SHA256 signed request with `X-HV-*` headers | Replay attacks; body/path substitution; forged requests from any non-cert-holder |

### `signed` mode — canonical request and what each field binds

`sign_request` in `backend/honeycore/transport.py` produces four `X-HV-*` headers:

```
X-HV-Cert       base64(PEM of api-client cert)
X-HV-Timestamp  integer Unix seconds
X-HV-Nonce      URL-safe base64(16 random bytes)
X-HV-Signature  base64(DER ECDSA-P256 sig over canonical_request)
```

The **canonical request** (`canonical_request()` in `transport.py`) binds the signature to the
exact call:

```
METHOD\n
PATH_WITH_QUERY\n
TIMESTAMP\n
NONCE\n
SHA256HEX(body)
```

| Bound field | Attack blocked |
|-------------|----------------|
| `NONCE` | **Replay** — `ReplayCache(ttl_seconds=300)` in `honeychecker/app/security.py` rejects any nonce seen in the past 5 minutes |
| `TIMESTAMP` | **Delayed replay / clock-skew replay** — `verify_signed_request` rejects requests where `|now − timestamp| > 60 s` (`max_skew=60`) |
| `SHA256HEX(body)` | **Body substitution** — altering the POST body invalidates the signature |
| `PATH_WITH_QUERY` | **Path substitution** — routing the request to a different endpoint invalidates the signature |
| Cert → Service CA chain | **Cert impersonation** — the cert is verified against the Service CA trust store before the signature; an attacker cannot substitute their own cert |

### `mtls` mode — compose verification record

The mTLS setup was verified end-to-end via `backend/scripts/verify_mtls.py` (`pki/README.md`
§Verified run):

| Test | Result |
|------|--------|
| No client cert | PASS (rejected at TLS handshake) |
| With api-client cert (Service CA) | PASS (admitted) |
| With throwaway cert (not Service CA) | PASS (rejected at TLS handshake) |

### `plain` mode prohibition

`plain` **must never be set outside local development** (ADR-005 §Consequences).
`verify_caller` in `honeychecker/app/security.py` (line 127) returns immediately with no checks
in this mode. CI and staging deploys must assert `HC_TRANSPORT != plain`. Note that no runtime
guard yet rejects `HC_TRANSPORT=plain` outside development; this is tracked as a residual risk
(§5 below).

---

## Known residual risks (network/PKI)

> Source: `docs/decisions/ADR-005.md`, `docs/decisions/ADR-006.md`, `backend/app/rate_limit.py`, `.env.example`.

### 1 — Server-held identity keys (ADR-006)

Each user's P-256 identity private key is wrapped with **`KEY_WRAP_SECRET`** (AES-256-GCM,
32-byte server KEK held in env vars, never in the DB). This was chosen because:

- Wrapping under the **master password** would produce a verifiable AES-GCM ciphertext —
  restoring the offline oracle that Honey Encryption is designed to eliminate (crypto invariant §1).
- Wrapping under the **login password** would let an attacker verify login-password guesses,
  weakening the honeyword alarm.

**Residual risk:** A full server compromise (DB access + env access) exposes all wrapped identity
keys. KEK rotation requires re-wrapping every key (script, future work). This is explicitly
out of scope per the threat model and ADR-006 §Consequences.

### 2 — Rate limiter keyed by Render's proxy IP (staging)

`backend/app/rate_limit.py` uses `slowapi` with `key_func=get_remote_address`. On Render, all
inbound traffic arrives through Render's shared proxy, so `get_remote_address` returns the
**proxy IP** rather than the true client IP.

**Effect:** The default limits (`RATE_LIMIT_LOGIN=5/minute`, `RATE_LIMIT_UNLOCK=10/minute` in
`.env.example`) would be shared across every user behind the same proxy and would trigger almost
immediately under any real load.

**Staging mitigation:** Limits are raised to **20/minute (login)** and **30/minute (unlock)** in
the staging `.env`. This is a partial workaround; trusting `X-Forwarded-For` from upstream proxies
via uvicorn's `--forwarded-allow-ips '*'` allows per-client rate limits but introduces header-spoofing
risks (see §6 below). Production deployments must audit this before go-live.

### 3 — Staging secrets must be regenerated for production

The staging deployment uses generated values for `KEY_WRAP_SECRET`, `JWT_SECRET`,
`HC_CLIENT_KEY_B64`, and all CA key env vars (`ISSUING_CA_KEY_B64`, `HC_TRUSTED_CA_CERT_B64`).
**These must be independently regenerated** for any production environment — staging and
production must never share a KEK, JWT secret, or service keypair. Reusing staging secrets
breaks environment isolation and could allow a staging compromise to yield production identity
keys. See `.env.example` for generation commands.

### 4 — Free-tier cold starts (Render)

Render free-tier services spin down after ~15 minutes of inactivity and cold-start on the next
request. Cold starts introduce a multi-second delay before the honeychecker responds. If the
honeychecker does not respond within `HONEYCHECKER_TIMEOUT_SECONDS`,
`backend/app/services/honeychecker_client.py` raises `HoneycheckerUnavailable` on timeouts or
5xx responses, causing login to return `503 Service Unavailable` (**fail-closed**).

During a cold start, login can fail with 503 — an **availability cost, not a security gap**;
decoy logins will not slip through uninspected, nor can an attacker bypass the honeyword alarm.

**Mitigation options:** Keep-alive pings or upgrading to a paid Render tier remain mitigations to
prevent cold-start delays and maintain service availability.

### 5 — No runtime guard rejecting `HC_TRANSPORT=plain` outside development

While `plain` mode is prohibited in non-development environments (ADR-005), no runtime guard yet
rejects `HC_TRANSPORT=plain` outside development. Enforcement currently relies on deployment
configuration and CI assertions. Adding an explicit runtime guard or startup assertion that rejects
`plain` mode when running in non-development environments remains a residual operational risk.

### 6 — Rate limit evasion via `X-Forwarded-For` spoofing (Render)

On Render, uvicorn trusts `X-Forwarded-For` (`--forwarded-allow-ips '*'`), needed so rate limits
are per client rather than collapsed to Render's shared proxy IP. However, because uvicorn trusts
the header, a client could spoof the `X-Forwarded-For` header to dodge per-IP rate limits. This
residual risk is accepted for the academic deployment.

