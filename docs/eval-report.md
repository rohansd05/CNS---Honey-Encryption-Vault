# Evaluation report

> Owner: T1 (Dhruv; chi-squared by Nidhi). Numbers come from `backend/eval/results/latest.json`
> (full run, 2026-10-14T16:11:22Z, `meta.git_commit` `91e3171` plus this branch's eval changes),
> produced by `python -m eval.run_all`. Metrics are defined in PROJECT-BRIEF.md §11. Seed
> uniformity fails for both models, and the official password and username distinguisher numbers
> miss their target. This report gives those numbers unchanged and explains them.

## Summary

| Check (§11) | Target | Result | Verdict |
|---|---|---|---|
| Round-trip `decode(encode(x)) == x` | 100% | **100%** (25,000 / 25,000, all held-out) | ✅ |
| `decode` totality on random seeds | 100% | **100%** (60,000 seeds, 0 failures) | ✅ |
| χ² (a) seed uniformity, held-out passwords | p > 0.05 | **p = 1.7 × 10⁻¹¹** (bytes) | ❌ model fit (codec control passes, p = 0.37) |
| χ² (a) seed uniformity, held-out usernames | p > 0.05 | **p = 5.1 × 10⁻⁷⁶** (bytes) | ❌ model fit (codec control passes, p = 0.13) |
| χ² (b) decoded templates vs model | p > 0.05 | **p = 0.92** passwords, **0.31** usernames | ✅ |
| Password distinguisher, official protocol (best of LR / RF) | ≤ 0.60 (ideal 0.50) | **0.740** (RF), 0.517 (LR) | ❌ |
| Password distinguisher, grouped CV / distinct strings | ≤ 0.60 | **0.517** / **0.544** (best of LR / RF) | ✅ supplementary (§4.3) |
| Username distinguisher, official / grouped / distinct | ≤ 0.60 | **0.827** / **0.728** / **0.759** | ❌ email suffix (§4.4) |
| Username distinguisher **without domain**, official / grouped / distinct | ≤ 0.60 | **0.783** / **0.553** / **0.557** | grouped / distinct ✅ (§4.4) |
| Dictionary attack: conventional vault | cracks | **cracked at guess #193 / 500** | ✅ |
| Dictionary attack: honey vault | no oracle | **500 distinct vaults from 500 guesses** | ✅ |
| Unlock p95, `default` KDF profile | < 1.5 s | **152 ms** (in-process) | ✅ |
| Unlock timing, right vs wrong master password (KS test) | p > 0.05 | **p = 0.87** `default`, **0.39** `server_lite`, **0.088** `demo` | ✅ (`demo` borderline, §4.5) |

## 1. Method

`backend/eval/run_all.py` runs every §11 measurement against the **real** honeycore through
`load_honeycore("real")`. It never uses the stub, whatever `HONEYCORE_IMPL` says, and writes one
strict-JSON file that `GET /api/eval/summary` serves.

| Section | What runs | Sample size (full) |
|---|---|---|
| `round_trip` | encode → decode on held-out passwords, held-out usernames and (username, password) entries; decode on uniform random seeds for the password, username and entry DTEs | 10,000 / 10,000 / 5,000; 20,000 seeds per DTE |
| `chi_squared` | `eval.chi_squared` (owner Nidhi): seed-byte (256 bins) and seed-int (top 4 bits, 16 bins) uniformity of encoded held-out values; codec control on model samples; template goodness of fit of decoded random seeds (top 50 templates + "other"); password and username models | n = 20,000 |
| `classifier` | `eval.classifier.run`: real held-out vs `model.sample()` decoys, 12 features, standardised logistic regression and 200-tree random forest, 5-fold CV under three protocols (§4.3). Usernames run twice: as stored, and `without_domain` (§4.4) | 10,000 per class |
| `attack` | `attack.simulator` on a fresh `demo`-profile honey vault and conventional vault with the same 8 synthetic entries; demo wordlist; real master password inserted at a random rank | 500 guesses |
| `kdf` | Argon2id derive time and 8-entry `HoneyVault.unlock` time per KDF profile | 15 reps per profile |
| `timing` | 8-entry `HoneyVault.unlock` with the right vs a fresh wrong master password, interleaved, per KDF profile; two-sample Kolmogorov-Smirnov test; a second right sample as A/A control; entry-DTE decode alone on real vs random seeds (§4.5) | 200 per class per profile; 2,000 decode rounds |

A "pass" for a χ² or KS test means p > 0.05, i.e. the test found no evidence of a difference.
The distinguisher's headline accuracy is the **stronger** of the two classifiers. An attacker
would use the better tool, so that is the honest number.

## 2. Setup

| Item | Value |
|---|---|
| Corpus | Passwords: SecLists RockYou, Zipf-ranked weights (`w = 1/rank^0.9`), §7.3. Usernames: SecLists `xato-net-10-million-usernames`, Zipf-ranked, §7.4 |
| Held-out split | `pcfg.is_heldout` (sha256-based, ~20%), never trained on. `data/processed/heldout_passwords.tsv` and `heldout_usernames.tsv`, 50,000 valid values each |
| Held-out usernames | Produced by `train_pcfg.py --kind username` (1M lines, `--format plain`) with `--out` pointing at a temporary file. That temporary model was identical to the committed `pcfg_username_v1`, so the split is exactly the one the committed model never saw |
| Models | `pcfg-password-v1`, `pcfg-username-v1`; entry seed 532 B (268 + 264) |
| Entry DTE | `honeycore.dte.entry_dte.PCFGEntryDTE` (`meta.entry_dte_impl`), the same one the vault uses |
| KDF profiles | `default` t=3, 64 MiB, p=4; `server_lite` t=2, 19 MiB, p=1; `demo` t=1, 8 MiB, p=1 |
| Hardware | Intel Core i9-14900HX, 16 GB RAM, Windows 11, Python 3.12.10 (scikit-learn 1.9.1, SciPy 1.18.1, NumPy 2.5.3) |
| Seed | 7 (NumPy RNG for held-out sampling, random seeds, CV folds). Decoys, salts, nonces and the attack and timing passwords use `secrets`, so classifier, attack and timing numbers vary slightly between runs. |
| Runtime | 208 s (classifier 113 s, timing 74 s) |

## 3. Results

### 3.1 Round-trip and totality

| DTE | Round-trip trials | Exact matches | Rate | Random seeds | Failed decodes |
|---|---|---|---|---|---|
| Password (held-out) | 10,000 | 10,000 | 1.000 | 20,000 | 0 |
| Username (held-out) | 10,000 | 10,000 | 1.000 | 20,000 | 0 |
| Entry (532 B, held-out pairs) | 5,000 | 5,000 | 1.000 | 20,000 | 0 |
| **Total** | **25,000** | **25,000** | **1.000** | **60,000** | **0** |

Every seed had the fixed length (0 wrong-length seeds), and every decoded value was a valid
1–32-character printable field.

### 3.2 Chi-squared

| Model | Test | n | χ² | dof | p | Pass |
|---|---|---|---|---|---|---|
| password | seed byte uniformity (held-out) | 20,000 | 434.4 | 255 | 1.7 × 10⁻¹¹ | ❌ |
| password | seed int uniformity (held-out, used ints) | 20,000 | 417.7 | 15 | 1.3 × 10⁻⁷⁹ | ❌ |
| password | seed int uniformity **control** (model samples) | 20,000 | 16.1 | 15 | 0.374 | ✅ |
| password | template goodness of fit (decoded random seeds) | 20,000 | 36.4 | 50 | 0.925 | ✅ |
| username | seed byte uniformity (held-out) | 20,000 | 920.5 | 255 | 5.1 × 10⁻⁷⁶ | ❌ |
| username | seed int uniformity (held-out, used ints) | 20,000 | 1,364.9 | 15 | 6.0 × 10⁻²⁸² | ❌ |
| username | seed int uniformity **control** (model samples) | 20,000 | 21.2 | 15 | 0.131 | ✅ |
| username | template goodness of fit | 20,000 | 54.5 | 50 | 0.306 | ✅ |

Top password templates. "Model" is P(PCFG) × P(template). "Decoys" is 20,000 decoded random
seeds. "Held-out" is 20,000 weighted held-out samples.

| Template | Model | Decoys | Held-out | Held-out ÷ model |
|---|---|---|---|---|
| L6 (6 letters) | 21.19% | 21.02% | 21.34% | 1.01 |
| L7 | 12.62% | 12.67% | 15.07% | 1.19 |
| D6 (6 digits) | 12.02% | 12.12% | 9.05% | 0.75 |
| L8 | 11.33% | 11.10% | 11.33% | 1.00 |
| L9 | 4.88% | 4.84% | 4.21% | 0.86 |
| L5 | 4.30% | 4.38% | 5.84% | 1.36 |
| L6D1 | 2.64% | 2.63% | 3.16% | 1.19 |
| D5 (5 digits) | 2.59% | 2.61% | 0.33% | **0.13** |
| L6D2 | 2.37% | 2.51% | 2.73% | 1.15 |
| L10 | 2.32% | 2.32% | 2.14% | 0.92 |
| L5D2 | 2.20% | 2.44% | 1.99% | 0.90 |
| L5D1 | 2.11% | 2.21% | 2.72% | 1.29 |
| D8 | 2.07% | 2.07% | 1.70% | 0.82 |
| L4D2 | 1.95% | 1.96% | 1.87% | 0.96 |
| L7D1 | 1.86% | 1.89% | 1.96% | 1.05 |

### 3.3 Distinguisher (10,000 real vs 10,000 decoys per field, 5-fold CV)

Accuracy is mean ± sd over the 5 folds. The three protocols are explained in §4.3.

**Passwords**

| Protocol | Rows | Logistic regression (acc / AUC) | Random forest (acc / AUC) |
|---|---|---|---|
| With replacement (official, `metrics`) | 20,000 (11,455 distinct strings) | 0.517 ± 0.010 / 0.528 | **0.740 ± 0.005 / 0.805** |
| Grouped by string (`grouped_results`) | 20,000 (11,455 groups) | 0.462 ± 0.062 / 0.454 | **0.517 ± 0.045 / 0.509** |
| Distinct strings only (`distinct_results`) | 5,687 per class | **0.544 ± 0.003 / 0.567** | 0.507 ± 0.009 / 0.519 |

For the official protocol, the random forest's precision is 0.730 and its recall 0.762 ("real" is
the positive class). They come from one extra CV pass with the same features, folds and seed and a
fresh set of decoys. The distinct protocol starts from 6,007 distinct real and 5,687 distinct
decoy strings and subsamples the larger class.

**Usernames, as stored** (`classifier.username`)

| Protocol | Rows | Logistic regression (acc / AUC) | Random forest (acc / AUC) |
|---|---|---|---|
| With replacement | 20,000 | 0.734 ± 0.004 / 0.793 | **0.827 ± 0.005 / 0.915** |
| Grouped by string | 20,000 (11,998 groups) | **0.728 ± 0.011 / 0.782** | 0.563 ± 0.088 / 0.713 |
| Distinct strings only | 4,378 per class (of 4,378 real, 7,681 decoy) | **0.759 ± 0.007 / 0.784** | 0.677 ± 0.006 / 0.763 |

**Usernames, known email domain stripped** (`classifier.username.without_domain`)

Same real sample (seed 7), fresh decoys. Before features, `eval.classifier.strip_known_domain`
removes `@domain` from any value whose domain is in the username model's own domain table, using
the model's §7.4 split (`pcfg.split_email`); other values are unchanged. It changed 0 of 10,000
real values and 4,554 of 10,000 decoys (45.5%) (`without_domain.transformed`).

| Protocol | Rows | Logistic regression (acc / AUC) | Random forest (acc / AUC) |
|---|---|---|---|
| With replacement | 20,000 | 0.571 ± 0.004 / 0.624 | **0.783 ± 0.004 / 0.863** |
| Grouped by string | 20,000 (10,430 groups) | **0.553 ± 0.059 / 0.575** | 0.546 ± 0.092 / 0.562 |
| Distinct strings only | 4,378 per class (of 4,378 real, 6,153 decoy) | **0.557 ± 0.011 / 0.580** | 0.528 ± 0.011 / 0.538 |

### 3.4 Dictionary attack (`demo` profile, 8 entries, 500 guesses from a 629-word list)

| | Conventional (AES-GCM) | Honey vault |
|---|---|---|
| Outcome | **CRACKED at guess #193** (= the real password's rank) | No guess can be singled out |
| Time | 1,413 ms (stops at the crack) | 3,580 ms for all 500 guesses (7.2 ms/guess) |
| Vaults produced | 1 (the real one; all 8 entries recovered) | **500 distinct vaults**, every one well-formed |
| Real password | Recognised by the AEAD tag | Recovers the real 8 entries, with no flag in the output |

### 3.5 KDF and unlock latency (in-process, ms)

| Profile | Params | Derive p50 / p95 | 8-entry unlock p50 / p95 |
|---|---|---|---|
| `default` (new vaults) | t=3, 64 MiB, p=4 | 85.1 / 202.0 | **54.5 / 151.5** |
| `server_lite` (honeywords) | t=2, 19 MiB, p=1 | 26.0 / 30.5 | 26.7 / 30.1 |
| `demo` (attack demo) | t=1, 8 MiB, p=1 | 7.5 / 12.7 | 7.5 / 8.2 |

Unlock time is about one KDF call. Decoding 8 entries adds well under 1 ms. With 15 reps the p95
is one or two slow calls: this run's `default` p95 (151.5 ms) is more than twice the previous
run's (61.8 ms), and the `timing` section's 200-sample p50s (§3.6) agree with these p50s.

### 3.6 Unlock timing: right vs wrong master password (`timing`, in-process, ms)

200 right and 200 wrong unlocks per profile on a fresh 8-entry vault, interleaved (order reversed
every other round); each wrong password is fresh and random, same length as the right one. "A/A"
compares the right sample with a second right sample taken in the same rounds.

| Profile | Right p50 / p95 | Wrong p50 / p95 | KS D | KS p (right vs wrong) | A/A control p | Same distribution |
|---|---|---|---|---|---|---|
| `default` | 53.2 / 195.8 | 53.7 / 199.7 | 0.060 | **0.866** | 0.466 | ✅ |
| `server_lite` | 27.3 / 54.6 | 27.2 / 52.7 | 0.090 | **0.394** | 0.965 | ✅ |
| `demo` | 5.98 / 8.34 | 5.93 / 7.78 | 0.125 | **0.088** | 0.142 | ✅ (borderline) |

Decode alone (`timing.decode_only_us`, 2,000 interleaved rounds, entry DTE only, no KDF): the 8
real entry seeds decode in **86.5 µs** p50 (p95 109.2), 8 random seeds in **44.9 µs** p50 (p95
54.4), KS p < 10⁻³⁰⁰. §4.5 explains what this does and does not leak.

## 4. Interpretation

### 4.1 What works
- **The DTEs are correct and total.** Every held-out password, username and entry round-trips
  exactly, and no random seed out of 60,000 fails to decode to a valid field. This is the
  property that makes `unlock()` unable to fail on a wrong password (AGENTS.md §1.2–1.3).
- **There is no offline oracle.** The conventional vault confirms the right password the
  moment it is tried (#193). The honey vault returns a complete, well-formed and *different*
  vault for every one of 500 guesses (500 / 500 distinct), and nothing marks the real one. §5
  traces why in the code.
- **Decoys follow the model** (template goodness of fit p = 0.92 for passwords, 0.31 for
  usernames). **The integer codec is unbiased** (control p = 0.37 and 0.13).
- **Latency is far below target.** p95 is 152 ms against a 1.5 s target, so there is headroom
  to raise the `default` Argon2 cost.
- **No detectable timing difference at the profiles real vaults use.** Right and wrong unlocks
  have the same latency distribution at `default` (p = 0.87) and `server_lite` (p = 0.39).

### 4.2 Seed uniformity fails because of model fit, not the codec
On held-out values the seed tests reject uniformity for both models (passwords: p ≈ 10⁻¹¹ for
bytes, 10⁻⁷⁹ for used ints; usernames: 10⁻⁷⁶ and 10⁻²⁸²). The control encodes values *sampled
from the model* through the same codec and passes (p = 0.37 and 0.13). The bias therefore comes
from real values having different frequencies from the model's probabilities, not from the
codec. For passwords the template table shows this directly. 5-digit passwords (`D5`) are 2.6% of
the model but 0.33% of held-out passwords. `D6` is over-weighted (12.0% vs 9.05%), while `L5`
and `L7` are under-weighted (×1.36 and ×1.19). For usernames, the email-domain choice (§4.4)
adds to it: real xato usernames never take a domain, so the first used int of every real seed
falls in the same "no domain" band.

This does not leak through the ciphertext. Seeds are XORed with an AES-CTR keystream, so the
stored bytes are uniform whatever the seed. The mismatch matters at the *decoded* level: real
vaults and decoys come from slightly different distributions. §4.3 and §4.4 measure that.

<a id="43-distinguisher-0741-overall-mostly-from-repeated-strings-partly-from-real-mismatch"></a>

### 4.3 Password distinguisher: 0.740 with repeated strings, ~0.52–0.54 without them
All three protocols use the same features, classifiers and 5 folds. They differ in what the
classifier may see.

- **With replacement (official §11 number): 0.740.** Real passwords are drawn *by weight with
  replacement* and decoys are `model.sample()`, so popular strings repeat. The 20,000 rows hold
  only 11,455 distinct strings. Plain stratified folds put copies of the same string in both the
  training and the test fold. Several features are close to unique per string
  (`mean_char_unigram_logprob`, `template_logprob`, `shannon_entropy`), so the random forest can
  memorise "this string was labelled real (or decoy)" and recognise it in the test fold. Logistic
  regression cannot memorise and stays near chance (0.517). The protocol rewards string-level
  memory and frequency differences. An attacker holding a leaked password list has the same
  kind of knowledge, so this stays the official number.
- **Grouped by string: 0.517 (RF), 0.462 (LR).** `StratifiedGroupKFold` with one group per
  distinct string, so every copy of a string, real or decoy, sits in one fold. The test fold
  only holds strings the classifier never saw, still in their real-world proportions.
  Memorisation is impossible, and the forest drops from 0.740 to 0.517. Logistic regression
  lands *below* chance (AUC 0.45). That carries no usable signal. Grouping puts popular strings,
  with hundreds of copies, into a single fold, so the class balance and the accuracy swing from
  fold to fold (sd 0.062 against 0.010 above). 0.462 is about 1.4 standard errors below 0.5.
- **Distinct strings only: 0.544 (LR), 0.507 (RF).** Each class is reduced to its distinct
  strings (6,007 real, 5,687 decoy), both subsampled to 5,687, and every string counts once.
  This asks whether decoy passwords *look* different from real ones, whatever their frequency.
  Both classifiers are near chance. The small linear edge fits the template mismatch in §4.2
  (too many all-digit decoys, too few short letter strings).

**Bottom line.** Most of the gap between 0.740 and 0.5 is memorisation of repeated strings: take
it away and the best classifier reaches 0.517 (grouped) or 0.544 (distinct), inside the ≤ 0.60
target. The remaining 2–4 points above chance are a real but small mismatch between the model
and real passwords, the same one the χ² seed tests detect. The decoys' *frequency* distribution
also differs from the real one, and a frequency-aware attacker can use that when ranking
candidate vaults. We report 0.740 as the official §11 number and give the other two alongside
it, not instead of it.

### 4.4 Username distinguisher: the email-domain suffix gives decoys away
As stored, real and decoy usernames separate under every protocol: 0.827 / 0.728 / 0.759
(official / grouped / distinct, best classifier). Unlike passwords, the signal survives grouping
and deduplication, and logistic regression already finds it, so it is not memorisation.

The cause is the email-domain step of the username model (§7.4). It appends a domain from the
fixed built-in table (`pcfg.email_domain_weights`) to a share of decoys, while the xato corpus is
bare usernames. The `without_domain` run now measures this in `latest.json` (it replaces the
ad-hoc check in the previous report):

| | As stored | Known domain stripped |
|---|---|---|
| Values changed by stripping | — | real 0 / 10,000, decoys 4,554 / 10,000 |
| With replacement (best) | 0.827 (RF) | 0.783 (RF); LR 0.734 → **0.571** |
| Grouped by string (best) | 0.728 (LR) | **0.553** (LR) |
| Distinct strings only (best) | 0.759 (LR) | **0.557** (LR) |

Without the suffix, grouped and distinct accuracy fall inside the ≤ 0.60 target and close to the
password numbers. What remains is the same pattern as §4.3: logistic regression's
with-replacement accuracy drops to 0.571, so most of the forest's 0.783 is memorisation of
repeated strings, and a few points of real local-part mismatch are left.

This is a mismatch between the model and *this test set*. It is not necessarily a mismatch with
real vaults, where many logins are email addresses (one of the eight demo entries is). The
held-out set cannot say whether 45% is the right email share. Stripping is an analysis tool, not
a fix: the deployed DTE still emits the suffix, so the as-stored numbers are the honest ones for
this test set. Two ways forward, both owned by the username DTE track (Nidhi): calibrate the
domain share on login data that includes email addresses, or evaluate local parts and domains
separately.

### 4.5 Timing: no difference at `default`; a small, value-dependent decode cost
At `default` and `server_lite` the KS test finds no difference between right and wrong unlocks
(p = 0.87 and 0.39). The A/A controls (0.47, 0.97) show the test is not over-sensitive here.

`demo` is borderline. It passes in `latest.json` (p = 0.088), but in four runs of the same
measurement during development (not kept in `latest.json`) it rejected every time (p = 0.001 to
0.012, right ~0.1 ms slower at p50), while its A/A control never did. One of those runs also
rejected at `default` (p = 0.030), but repeats gave p = 0.55, 0.997 and 0.55, and an A/A control
in the same batch also hit 0.030. We read `default` as noise and `demo` as a real, small effect.

`decode_only_us` explains the effect. Decoding the 8 real entries takes about 42 µs longer than
decoding 8 random seeds (86.5 vs 44.9 µs p50). The decode does **not** exit early: it always
decodes every entry, and no branch depends on whether the key is right (§5). But how much work
it does depends on the *decoded value*. `_PCFGBase._decode_block` reads more codec choices for a
value spelled character by character (the chars fallback, or a template not in the model) than
for a common bucket word. The demo entries are deliberately unusual strings (`Gh!tide2026`,
`cl0ud&Rain!`), and random seeds mostly decode to common templates. 42 µs is about 0.7% of a
`demo` unlock and lost in the KDF's jitter at `default` (p95 − p50 ≈ 140 ms in this run).

What it leaks: decode time is, up to small noise, a function of the decoded vault, and every
unlock already returns that decoded vault. Timing tells an attacker roughly what the output
already tells them: how "model-typical" the decoded credentials are, the mismatch §4.3–4.4
measure. It is not a "correct password?" oracle. A strict reading of AGENTS.md §1.2 ("timing
class") would still want constant work. A constant-work decode (always consume every seed int)
is an option for honeycore (T1) if `demo` ever runs on a deployed instance.

## 5. Invariant audit: the honey-vault decrypt path

Traced from the API to the DTE (AGENTS.md §1.1–1.4), at commit `91e3171`:

| Step | Code (file:function) | MAC / tag / padding / checksum? | Depends on whether the key is right? |
|---|---|---|---|
| API | `backend/app/api/vault.py:unlock_vault_endpoint` | none | No. Always 200 with the same `UnlockResponse` shape; never logs the body |
| Service | `backend/app/services/vault_service.py:unlock_vault` | none | No. Loads the vault and returns `vault.unlock(...)`, no branch on the result |
| Vault | `backend/honeycore/vault.py:HoneyVault.unlock` | none | No. Derives the key once, then decrypts and decodes **every** entry in a plain loop: no comparison, no `break`, no `try` |
| KDF | `HoneyVault._keys` → `vault.py:_kdf_password` → `backend/honeycore/kdf.py:Argon2KDF.derive` → `kdf.py:derive_subkeys` | none; nothing derived is stored | No. `_kdf_password` maps lone surrogates so encoding cannot fail. `derive` checks only the salt length, which `from_dict` fixes. `derive_subkeys` is HMAC-SHA256 with fixed labels |
| Cipher | `backend/honeycore/cipher.py:AESCTRCipher.apply` | none: AES-256-CTR, no tag, length-preserving | No. Checks only the key (always 32 B) and nonce (16 B, fixed at load) lengths |
| Entry DTE | `backend/honeycore/dte/entry_dte.py:PCFGEntryDTE.decode` | none | No. Checks only that the seed is `ENTRY_SEED_LEN` (532 B), which `from_dict` and CTR guarantee |
| Field DTEs | `dte/username_dte.py:PCFGUsernameModel.decode`, `dte/password_dte.py:PCFGPasswordModel.decode` → `dte/pcfg.py:_PCFGBase._decode_block` → `dte/int_codec.py:decode_choice` | none: no padding or checksum to verify | No early exit. `decode_choice` is `bisect_right(cum, r % total)`, defined for every 32-bit int. The *amount* of work depends on the decoded value (§4.5) |
| Sigil | `backend/honeycore/sigil.py:compute_sigil` | none | No. Any 32-byte key gives a sigil; it raises only for a wrong key length, which `derive_subkeys` cannot produce |
| Blob | `vault.py:HoneyVault.to_dict` / `from_dict` | none: entries hold only id, service, nonce, ciphertext, timestamps; no verifier or key hash | `from_dict` errors depend only on the blob, never on a password |

Findings:
- **No integrity check anywhere on the path.** There is no MAC, tag, padding check, checksum,
  magic bytes or stored verifier, so any password yields some seed, and the total DTE turns it
  into a well-formed vault. §3.1 tests that totality (60,000 random seeds, 0 failures). §3.4
  shows the consequence (500 / 500 distinct vaults).
- **No early exit on a wrong key.** Every entry is always decrypted and decoded. The only checks
  that can raise are lengths fixed when the blob is loaded, never anything derived from the
  password.
- **Timing:** no measurable right-vs-wrong difference at `default` or `server_lite` (KS p = 0.87,
  0.39). At `demo`, a small value-dependent decode cost (~42 µs per 8 entries) is sometimes
  detectable. It reflects the decoded output, not a key check (§4.5).

The AES-GCM uses (`honeycore/baseline.py` conventional vault, share envelopes, key wrapping) are
outside this path, as AGENTS.md §1.9 allows.

## 6. Limitations
- **Seed uniformity fails for both models (§4.2).** The codec control passes, so the codec
  is sound. The failure is model fit, so real seeds are not uniform before encryption. The
  ciphertext is unaffected (AES-CTR), but decoded real values and decoys come from different
  distributions. This is an open issue, not fixed by this change.
- **Username email domain (§4.4).** The deployed username DTE adds a known email domain to about
  45% of decoys, and no real xato username has one. As stored, usernames miss the target under
  every protocol (best 0.827 / 0.728 / 0.759). `without_domain` shows that the suffix is the
  cause; it does not fix it. xato cannot tell us the right email share. The username DTE track
  owns this.
- **Held-out password weights ≠ training weights.** `heldout_passwords.tsv` is byte-identical
  to the held-out split of `rockyou-withcount` (real counts). The committed password model does
  *not* match a `rockyou-withcount` retrain, which fits its recorded Zipf rank weights. Weighted
  real samples therefore follow real frequencies, while the model follows rank-based ones. Part
  of the frequency mismatch in the official 0.740 and in χ² (a) may come from this. Retraining
  the password model on `rockyou-withcount` and re-running would settle it.
- **Value-dependent decode time (§4.5).** Not a key oracle, but the decode is not constant-work.
  It is borderline detectable at `demo` and not at `default`.
- **Independent fields:** decoy entries are independent, so password reuse across entries is
  not modelled (§13). A distinguisher working at vault level, not per credential, could do
  better than these per-field numbers. This evaluation does not measure that.
- **Latency and timing are in-process,** on a fast laptop (i9-14900HX) that was not otherwise
  idle. They do not include HTTP, the honeychecker, or Render's smaller instances, where network
  jitter would hide a 42 µs difference but could add others. §11 asks for a separate measurement
  on the deployed API. The 15-rep `kdf` p95 is sensitive to one or two slow calls (§3.5).
- **Run-to-run variation:** decoys, salts and the attack and timing passwords use `secrets`, so
  the classifier, attack and timing numbers vary between runs (fold sd ≈ 0.005 for the plain
  protocols, ≈ 0.05–0.09 for grouped CV; the `demo` KS p-value has ranged from 0.001 to 0.09).
  The real password's rank in the attack is random.
- **`dataset.training_samples` is `null`:** the model files don't record their training size.

## 7. Reproduction

```bash
# from backend/, venv active. Held-out files in data/processed/ (gitignored):
python scripts/download_corpus.py --passwords none --usernames seclists-xato
python scripts/train_pcfg.py --kind username --input ../data/raw/xato-net-10-million-usernames.txt \
    --format plain --max-lines 1000000 --out /tmp/pcfg_username_tmp.json.gz
#   ^ --out elsewhere keeps the committed model untouched; heldout_usernames.tsv is the output we keep

python -m eval.run_all            # full run (~210 s here), writes eval/results/latest.json
python -m eval.run_all --quick    # tiny sizes; also writes latest.json unless --out given
python -m eval.run_all --quick --out /tmp/quick.json   # leave latest.json untouched

# individual pieces
python -m eval.chi_squared -n 20000
python -m eval.classifier -n 10000   # three protocols, password + username (as stored only)

# serve it
uvicorn app.main:app --port 8000   # GET /api/eval/summary returns latest.json
```

Options: `--seed N` (default 7), `--heldout-passwords PATH`, `--heldout-usernames PATH`. Tests:
`pytest tests/core/test_run_all.py tests/core/test_classifier.py` (synthetic held-out data,
quick mode).
