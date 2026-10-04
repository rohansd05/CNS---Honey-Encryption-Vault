"""Train the password PCFG model (PROJECT-BRIEF.md §7.3). Owner: T1 — Nidhi.

Usage (from backend/)::

    python scripts/train_pcfg.py --kind password \\
        --input ../data/raw/rockyou-withcount.txt.bz2 --format withcount \\
        --max-lines 1000000 --out honeycore/models/pcfg_password_v1.json.gz

Input may be plain text, ``.bz2`` or ``.gz``. ``withcount`` lines look like ``"  12345 pw"``;
``plain`` lists are ranked, so line ``r`` gets the Zipf weight ``(N / r) ** 0.9`` (i.e.
``1/r**0.9`` scaled so the last line weighs 1). Lines are decoded as latin-1; only valid
fields (1..32 printable ASCII) are kept. Held-out passwords (``pcfg.is_heldout``, ~20%) are
NEVER trained on; up to ``--heldout-max`` of them are written with their weights to
``data/processed/heldout_passwords.tsv`` (``password<TAB>weight``) for evaluation.

Never print corpus lines: the summary reports counts only.
"""

from __future__ import annotations

import argparse
import bz2
import gzip
import re
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import IO

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
if str(BACKEND) not in sys.path:  # allow `python scripts/train_pcfg.py`
    sys.path.insert(0, str(BACKEND))

from honeycore.dte.pcfg import (  # noqa: E402
    is_heldout,
    is_valid_field,
    save_model,
    train_password_model,
)

WITHCOUNT_RE = re.compile(r"^\s*(\d+) (.*)$")
ZIPF_EXPONENT = 0.9
MAX_MODEL_BYTES = 10 * 1024 * 1024
DEFAULT_OUT = BACKEND / "honeycore" / "models" / "pcfg_password_v1.json.gz"
DEFAULT_HELDOUT = REPO / "data" / "processed" / "heldout_passwords.tsv"


def open_corpus(path: Path) -> IO[bytes]:
    """Open plain, ``.bz2`` or ``.gz`` files as a binary stream."""
    if path.suffix == ".bz2":
        return bz2.open(path, "rb")
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return path.open("rb")


def parse_withcount(line: str) -> tuple[str, int] | None:
    """Parse ``"   12345 password"`` -> ``("password", 12345)``; ``None`` if malformed."""
    m = WITHCOUNT_RE.match(line)
    if not m:
        return None
    count = int(m.group(1))
    return (m.group(2), count) if count > 0 else None


def zipf_weight(rank: int, n: int) -> float:
    """Zipf weight ``1/rank**0.9`` scaled so rank ``n`` weighs 1 (count-like units)."""
    return (n / rank) ** ZIPF_EXPONENT


def read_corpus(
    stream: IO[bytes], fmt: str, max_lines: int, stats: dict[str, int]
) -> Iterator[tuple[str, float]]:
    """Yield ``(password, weight)`` for the first ``max_lines`` lines (all valid fields).

    Updates ``stats``: ``lines``, ``malformed``, ``invalid``, ``valid``.
    """
    for rank, raw in enumerate(stream, start=1):
        if rank > max_lines:
            break
        stats["lines"] += 1
        line = raw.decode("latin-1").rstrip("\r\n")
        if fmt == "withcount":
            parsed = parse_withcount(line)
            if parsed is None:
                stats["malformed"] += 1
                continue
            password, weight = parsed
        else:
            password, weight = line, zipf_weight(rank, max_lines)
        if not is_valid_field(password):
            stats["invalid"] += 1
            continue
        stats["valid"] += 1
        yield password, weight


def split_heldout(
    pairs: Iterator[tuple[str, float]],
    heldout_out: IO[str] | None,
    heldout_max: int,
    stats: dict[str, int],
) -> Iterator[tuple[str, float]]:
    """Pass training pairs through; divert held-out ones to ``heldout_out`` (never trained on).

    Updates ``stats``: ``kept``, ``heldout``, ``heldout_written``.
    """
    for password, weight in pairs:
        if is_heldout(password):
            stats["heldout"] += 1
            if heldout_out is not None and stats["heldout_written"] < heldout_max:
                w = str(weight) if isinstance(weight, int) else f"{weight:.6g}"
                heldout_out.write(f"{password}\t{w}\n")
                stats["heldout_written"] += 1
            continue
        stats["kept"] += 1
        yield password, weight


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 if the model exceeds 10 MB."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--kind", choices=["password"], default="password")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--format", choices=["withcount", "plain"], default="withcount")
    ap.add_argument("--max-lines", type=int, default=1_000_000)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--heldout-out", type=Path, default=DEFAULT_HELDOUT)
    ap.add_argument("--heldout-max", type=int, default=50_000)
    args = ap.parse_args(argv)
    if args.max_lines < 1:
        ap.error("--max-lines must be >= 1")

    stats = dict.fromkeys(
        ["lines", "malformed", "invalid", "valid", "kept", "heldout", "heldout_written"], 0
    )
    started = time.perf_counter()
    args.heldout_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        open_corpus(args.input) as stream,
        args.heldout_out.open("w", encoding="ascii", newline="\n") as heldout,
    ):
        pairs = read_corpus(stream, args.format, args.max_lines, stats)
        model = train_password_model(split_heldout(pairs, heldout, args.heldout_max, stats))
    size = save_model(model, args.out)
    elapsed = time.perf_counter() - started

    n_segments = sum(len(b) for by_len in model["segments"].values() for b in by_len.values())
    print("PCFG password model trained")
    print(f"  input            {args.input} ({args.format})")
    print(f"  lines read       {stats['lines']:,}")
    print(f"  malformed        {stats['malformed']:,}")
    print(f"  invalid fields   {stats['invalid']:,}  (not 1..32 printable ASCII)")
    print(f"  valid            {stats['valid']:,}")
    print(f"  kept (training)  {stats['kept']:,}")
    print(f"  held out         {stats['heldout']:,}  ({stats['heldout_written']:,} written)")
    print(f"  templates        {len(model['templates']):,}")
    print(f"  segment entries  {n_segments:,}  (incl. __CHARS__)")
    print(f"  model            {args.out} — {size:,} bytes ({size / 2**20:.2f} MiB gz)")
    print(f"  held-out file    {args.heldout_out}")
    print(f"  time             {elapsed:.1f} s")
    if size > MAX_MODEL_BYTES:
        print("  !! model exceeds 10 MB; lower --max-lines or top-K", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
