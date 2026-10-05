# pki/

Owner: **T4 — Parth**. Our own two-tier X.509 PKI (PROJECT-BRIEF.md §10).

Planned (Phase 1):
- `make_root_ca.py` — Root CA (P-256, 10 years). Created offline; its key never leaves `pki/out/`
  and is never deployed.
- Issuing CA (5 years, signed by Root) which issues:
  - user identity certificates (in-app, via `honeycore/pki.py`);
  - `honeychecker-server` (SAN: localhost, honeychecker);
  - `honeyvault-api` client certificate (EKU clientAuth).

Output goes to `pki/out/` — **gitignored**, together with every `*.pem`, `*.key`, `*.crt`,
`*.csr`, `*.p12`. Deployments receive certs as base64 env vars (`*_B64` in `.env.example`).

## Usage
From the root of the repository, run the following scripts to generate PKI materials:
```bash
python pki/make_root_ca.py
python pki/make_issuing_ca.py
python pki/issue_service_certs.py
python pki/export_env.py
```
