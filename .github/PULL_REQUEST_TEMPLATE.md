## What changed
<!-- One or two sentences. Link the issue: Closes #… -->

**Track:** T? · **Owner paths touched:** <!-- e.g. backend/honeycore/dte/ -->

## How it was tested
<!-- Commands + results, e.g. `cd backend && ruff check . && ruff format --check . && pytest` -->

## Screenshots (UI changes)

## Definition of done (AGENTS.md §6)
- [ ] Code + tests in the owning track's paths; `ruff`/`pytest` or `lint`/`build` pass locally.
- [ ] No crypto invariant (AGENTS.md §1) violated; no secrets in code, logs, or fixtures.
- [ ] Public functions documented; `docs/` updated if behaviour or API changed.
- [ ] Session summary below: files changed, commands run + results, deviations from the
      brief/contract, open TODOs for other tracks.

## Contract impact
- [ ] None
- [ ] Touches a frozen contract (`honeycore/interfaces.py`, `docs/api-contract.md`, vault blob /
      envelope / model format, env var names) → PR labelled `contract-change`, T1 lead + affected
      tracks requested as reviewers.

## Deviations / TODOs for other tracks
