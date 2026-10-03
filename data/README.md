# data/

Local-only folder for training/evaluation corpora. **Everything here except this README is
gitignored.**

## What goes here
- `data/raw/` — downloaded by `backend/scripts/download_corpus.py` (T1 Nidhi):
  - RockYou (prefer the `rockyou-withcount` frequency list) → password PCFG.
  - SecLists xato usernames → username model.
- `data/processed/` — train / held-out splits (20% held out for evaluation, never used to train).

Trained models are small and DO get committed, but under `backend/honeycore/models/`
(`pcfg_password_v1.json.gz`, `pcfg_username_v1.json.gz`, ≤ 10 MB gz), not here.

## Why it is gitignored
- Size: raw corpora are hundreds of MB.
- Sensitivity: they are real leaked passwords of real people.
- Licensing: redistribution terms are unclear; everyone downloads them from the original
  public sources with the script instead.

## Licence & ethics
These lists come from historical public breaches and are widely used in password research.
Use them **only** for training/evaluating our models in this academic project. Do not try to
link entries to individuals, do not use them against any live system, do not share copies, and
never paste corpus lines into issues, PRs, logs, test fixtures or screenshots. Test fixtures use
synthetic passwords only.
