# Demo script (5–7 min)

> Owner: T1 lead (Nidhi); Attacker Console parts with T3 (Chetan). Source: PROJECT-ROADMAP.md §10.
> Warm both Render services 5 minutes before recording (free tier sleeps after ~15 min).

| # | Segment | Time | What to show | Presenter |
|---|---|---|---|---|
| 1 | The problem (LastPass) | 30 s | Landing page story: 2022 breach, vaults cracked offline, >$35M lost; "a conventional vault tells the attacker when a guess is right". | TBD |
| 2 | Normal use | 60 s | Register (login ≠ master enforced), add entries, lock, unlock → real vault + your Sigil. | TBD |
| 3 | Typo → decoy | 30 s | Unlock with a one-character typo → a plausible but different vault, different Sigil, same HTTP 200 and similar latency. | TBD |
| 4 | Attacker console | 90 s | Steal the blob; dictionary attack: baseline AES-GCM vault "CRACKED at guess #n" vs honey vault producing a stream of plausible decoys with no signal. | TBD |
| 5 | Honeyword login → alarm | 45 s | Use a "cracked" decoy sweetword to log in → generic 401, breach alert appears in Admin and the console. | TBD |
| 6 | Secure sharing | 45 s | alice shares an entry with bob; bob opens it: signature + certificate valid. Tampered envelope rejected. | TBD |
| 7 | Evaluation + limitations | 60 s | Evaluation page (chi-squared, classifier accuracy, templates); limitations (typos, reuse, server-side crypto). | TBD |

## Pre-flight checklist
- [ ] `GET /api/health` → `honeycore_impl: "real"`, `honeychecker: "ok"`.
- [ ] Demo user seeded (`scripts/seed_demo.py`), bob exists for sharing.
- [ ] `DEMO_MODE=true` on the demo deployment.
- [ ] Latest `eval/results/latest.json` deployed.


## Attack Wordlist Builder

Generate the demo attack wordlist from the built-in base words:

```bash
python3 backend/scripts/build_attack_wordlist.py
The generated wordlist is written to:

`backend/attack/wordlists/demo_wordlist.txt`

The builder applies the configured mangling rules and limits the generated wordlist to 2,000 entries.