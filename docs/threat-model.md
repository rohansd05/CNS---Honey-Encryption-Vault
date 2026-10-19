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
| **A1** offline thief | Steals the API database: vault blobs, honeyword hashes, shares | Recover entries; confirm a master password guess offline | **Honey Encryption**: no MAC/checksum/key hash, eliminating the cryptographic verification oracle (every guess decrypts to a syntactically valid vault; resistance against statistical classifiers is bounded by model fit, see §Security claims). **Honeywords**: cracking the k hashes yields k candidates; logging in with a decoy raises a `HONEYWORD_LOGIN` alarm via the separate honeychecker. Argon2id slows every guess. |
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

## Model-version requirements & artifact integrity
- **Declared model identifiers in exported vaults**: Every exported vault blob v1 explicitly
  declares its DTE model identifiers (`dte.password_model` and `dte.username_model`, e.g.
  `"pcfg-password-v1"` and `"pcfg-username-v1"`).
- **Fail-closed validation on import**: `HoneyVault.from_dict()` validates the declared
  `password_model` and `username_model` against the active DTE engine. If a vault specifies an
  unsupported or mismatched model ID, import fails closed with `VaultFormatError` rather than
  silently attempting to decode with incompatible distributions.
- **Pre-load SHA-256 artifact integrity verification**: `honeycore.factory._require_model_files()`
  verifies model artifacts before loading into memory:
  1. The model ID must be registered in the approved `MODEL_INTEGRITY_MANIFEST`.
  2. The file name must match the approved manifest entry.
  3. The file must exist on disk (raising an actionable training command if missing).
  4. The computed SHA-256 digest must match the trusted hash (`MODEL_SHA256_MANIFEST`).
- **Model distribution dependency**: Honey Encryption maps seeds through cumulative distribution
  frequencies. Correct vault recovery strictly requires the exact probability distribution and
  weights used during encryption. Decoding an authentic ciphertext with a different model or
  retrained weights produces incorrect plaintext, even with the correct master password.
- **Canonical password model status**:
  - The `dev` branch repository currently commits and uses `pcfg-password-v1`
    (`pcfg_password_v1.json.gz`, SHA-256 `f2ba0b8ab81e06aded1b456c0dc1c8fbf0e46e10d21dd0628346994a64a7a83d`),
    trained on RockYou with Zipf rank weights.
  - The staging deployment evaluated `pcfg-password-v2` (`pcfg_password_v2.json.gz`, SHA-256
    `8b225bb35d85624a2da1f4a3611574f2895336030660f2a838a63a3f159e76a6`), trained on
    `rockyou-withcount` frequency counts.
  - The decision to formally promote `v2` as canonical across all environments remains an open
    team decision awaiting T1 lead approval. Until formally adopted, `v2` is not canonical and
    must not be assumed to be supported in every environment.

## Security claims & qualification
To ensure accurate security claims, HoneyVault distinguishes between cryptographic mechanics,
decoy generation, and statistical resistance:

1. **Encryption at rest**:
   - Vault entries are encrypted with AES-256-CTR using a dedicated random 16-byte nonce per entry.
   - Keystreams are derived from the master password using Argon2id (`honeycore/kdf.py`).
   - Ciphertext bytes are pseudorandom at rest.

2. **Absence of a cryptographic verification oracle**:
   - Conventional vaults (e.g. AES-GCM) provide an immediate, binary verification oracle: guessing
     an incorrect master password fails authentication tag verification or padding checks.
   - HoneyVault eliminates this oracle: there is no MAC, no AEAD authentication tag, no padding, no
     magic bytes, no checksum, and no stored hash of the master password or derived key.
   - Every candidate master password decrypts to a complete, syntactically valid vault.

3. **Total decoding & plausible decoy generation**:
   - `EntryDTE.decode()` is total over all 532-byte seeds (AGENTS.md §1.3).
   - Every possible byte sequence decodes without error into printable 1–32 character ASCII
     username and password strings matching the PCFG grammar structure.

4. **Statistical distinguishability vs. information-theoretic security**:
   - *Absence of an explicit cryptographic verification oracle does not imply information-theoretic
     security or absolute resistance to offline attacks.*
   - An offline attacker who steals a vault blob can apply statistical classifiers, language models,
     or frequency analyses across candidate decrypted vaults to rank plausible vs. implausible
     candidates.
   - As measured and documented in `docs/eval-report.md` (10,000 real held-out vs. 10,000 decoys,
     5-fold cross-validation):
     - **Passwords**: On the official protocol with replacement, Random Forest achieves **0.748**
       accuracy (AUC 0.816) due to string repetition and frequency skew in real leak data vs.
       synthetic PCFG sampling (Logistic Regression achieves 0.506). Under grouped CV (controlling
       for string memorisation), Random Forest accuracy drops to **0.545** (LR 0.473); on distinct
       strings only, accuracy is **0.516** (RF) and **0.544** (LR).
     - **Usernames**: Classifiers achieve **0.823** (official) / **0.738** (grouped) / **0.762**
       (distinct) accuracy because the model's email-domain heuristic assigns domains to ~45.3% of
       decoys, whereas the xato evaluation corpus contains only bare usernames without domains.
     - **Seed uniformity**: Chi-squared tests reject seed uniformity on real held-out data
       ($p = 6.8 \times 10^{-12}$ for passwords, $p = 4.7 \times 10^{-54}$ for usernames) because
       empirical password distributions diverge from the PCFG's probability weights. While
       ciphertext is uniform under AES-CTR, the decrypted plaintexts retain this statistical bias.

5. **Key structural limitations**:
   - **Model-distribution mismatch**: Real user passwords outside the training corpus or with
     different frequency distributions produce distinct statistical profiles from synthetic decoys.
   - **Vault-level entry independence vs. password reuse**: Entries are encrypted and decrypted
     independently. Real vaults frequently exhibit password reuse or shared root patterns across
     services; HoneyVault generates independent decoy credentials per entry, exposing a potential
     vault-level distinguishing signal.
   - **Out-of-distribution credentials**: Passwords with structures absent from the training corpus
     (e.g. high-entropy passphrases, machine-generated tokens) fall back to the unigram fallback path,
     which can alter the statistical signature compared to typical PCFG decoys.
