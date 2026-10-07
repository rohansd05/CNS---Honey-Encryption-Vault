# pki/

Owner: **T4 — Parth**. Our own two-tier X.509 PKI (PROJECT-BRIEF.md §10).

## CA Hierarchy and Trust Domains

HoneyVault uses **two completely separate CA hierarchies** — one for user identity,
one for service-to-service authentication. This is the key security property of Phase 4.

### 1. User-identity hierarchy (Root → Issuing CA → user cert)

| CA | Key | Validity | Purpose |
|----|-----|----------|---------|
| **Root CA** (`root_ca.crt`) | P-256 | 10 years | Offline trust anchor; key never deployed |
| **Issuing CA** (`issuing_ca.crt`) | P-256 | 5 years | Issues user identity certs in-app |
| **User cert** (CN = username) | P-256 | 1 year | ECDSA for secure entry sharing (§9) |

### 2. Service CA hierarchy (Service CA → service leaf certs)

| CA / Cert | Key | Validity | Purpose |
|-----------|-----|----------|---------|
| **Service CA** (`service-ca.crt`) | P-256 | 10 years | Trust anchor for service channel; key offline |
| **honeychecker-server** (`honeychecker-server.crt`) | P-256 | 1 year | uvicorn TLS server cert (SAN: localhost, honeychecker) |
| **api-client** (`api-client.crt`) | P-256 | 1 year | mTLS / signed-request client cert (EKU clientAuth) |

## Why Two Separate CAs?

The honeychecker's trust store (`HC_TRUSTED_CA_CERT_B64`) contains **only the Service CA**.
The user-identity trust store (Root CA) is **never** placed in the honeychecker's config.

**Consequence**: a user identity certificate (Root → Issuing CA → username) can **never**
build a valid chain to the Service CA, so it cannot authenticate to the honeychecker —
even if the attacker obtained a user cert with `CN=honeyvault-api`.

Without this separation, a user cert (legitimately issued, or forged under a compromised
Issuing CA) could impersonate the API to the honeychecker, silently bypassing the
alarm system. The separate Service CA is the cryptographic enforcement of that boundary.

## Scripts

Run from the **repository root** in order:

```bash
# User-identity PKI (run once, offline)
python pki/make_root_ca.py
python pki/make_issuing_ca.py

# Service PKI (run once, offline)
python pki/make_service_ca.py      # <-- NEW in Phase 4
python pki/issue_service_certs.py  # issues from Service CA (not Issuing CA)

# Export base64 env vars for deployment / CI
python pki/export_env.py
```

## Output layout (`pki/out/` — gitignored)

```
pki/out/
  root_ca.crt          Root CA cert          (user-identity trust anchor)
  root_ca.key          Root CA key           OFFLINE — never deploy
  issuing_ca.crt       Issuing CA cert       (deploy alongside API for cert issuance)
  issuing_ca.key       Issuing CA key        OFFLINE — never deploy
  service-ca.crt       Service CA cert       (honeychecker trust store)
  service-ca.key       Service CA key        OFFLINE — never deploy
  honeychecker-server.crt  Server TLS cert   (uvicorn --ssl-certfile)
  honeychecker-server.key  Server TLS key    deploy to honeychecker only
  api-client.crt       Client cert           (honeyvault-api → honeychecker; mTLS / signed)
  api-client.key       Client key            deploy to API only
```

`pki/out/` is gitignored together with every `*.pem`, `*.key`, `*.crt`, `*.csr`, `*.p12`.
Deployments receive certs as base64 env vars (`*_B64` in `.env.example`).
`HC_TRUSTED_CA_CERT_B64` = Service CA cert (not Root CA).
