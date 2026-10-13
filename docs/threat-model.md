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
