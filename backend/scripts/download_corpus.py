"""Download the training corpora into ``data/raw/`` (gitignored). Owner: T1 — Nidhi.

Usage (from backend/)::

    python scripts/download_corpus.py --passwords rockyou-withcount --usernames seclists-xato
    python scripts/download_corpus.py --passwords seclists-rockyou --usernames none
    python scripts/download_corpus.py --passwords file:C:/path/rockyou-withcount.txt

Files already present are skipped. For every file the script prints its size and SHA-256.
If a download fails, it prints instructions for fetching the file by hand and passing it with
``file:PATH``. See data/README.md for licence & ethics: these are real leaked passwords;
never paste lines from them anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
CHUNK = 1 << 20


@dataclass(frozen=True)
class Source:
    """A downloadable corpus: ``filename`` is the saved name; ``extract`` a tar member."""

    url: str
    filename: str
    extract: str | None = None
    note: str = ""


PASSWORD_SOURCES: dict[str, Source] = {
    "rockyou-withcount": Source(
        "https://downloads.skullsecurity.org/passwords/rockyou-withcount.txt.bz2",
        "rockyou-withcount.txt.bz2",
        note="frequency list, lines like '  290729 123456' (train with --format withcount)",
    ),
    "seclists-rockyou": Source(
        "https://github.com/danielmiessler/SecLists/raw/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz",
        "rockyou.txt.tar.gz",
        extract="rockyou.txt",
        note="ranked list, one password per line (train with --format plain)",
    ),
}
USERNAME_SOURCES: dict[str, Source] = {
    "seclists-xato": Source(
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/xato-net-10-million-usernames.txt",
        "xato-net-10-million-usernames.txt",
        note="one username per line",
    ),
}


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of ``path``."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def report(path: Path) -> None:
    """Print size and SHA-256 of ``path``."""
    size = path.stat().st_size
    print(f"  {path}")
    print(f"    size   {size:,} bytes ({size / 1e6:.1f} MB)")
    print(f"    sha256 {sha256_file(path)}")


def _progress(total: int | None, desc: str) -> Any:
    """Return a tqdm progress bar, or a tiny printing fallback if tqdm is missing."""
    try:
        from tqdm import tqdm

        return tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=desc)
    except ImportError:
        return _SimpleProgress(total, desc)


class _SimpleProgress:
    def __init__(self, total: int | None, desc: str) -> None:
        self.total, self.desc, self.n, self._last = total, desc, 0, -1

    def update(self, n: int) -> None:
        self.n += n
        if self.total:
            pct = 100 * self.n // self.total
            if pct != self._last and pct % 5 == 0:
                print(f"  {self.desc}: {pct}% ({self.n:,}/{self.total:,} bytes)", flush=True)
                self._last = pct

    def close(self) -> None:
        print(f"  {self.desc}: done ({self.n:,} bytes)", flush=True)


def download(url: str, dest: Path) -> None:
    """Stream ``url`` to ``dest`` via a ``.part`` file (atomic rename on success)."""
    if not url.startswith("https://"):
        raise ValueError("only https:// sources are allowed")
    part = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "honeyvault-download/1.0"})  # noqa: S310
    with urllib.request.urlopen(req, timeout=60) as resp, part.open("wb") as out:  # noqa: S310
        length = resp.headers.get("Content-Length")
        bar = _progress(int(length) if length else None, dest.name)
        try:
            while chunk := resp.read(CHUNK):
                out.write(chunk)
                bar.update(len(chunk))
        finally:
            bar.close()
    part.replace(dest)


def extract_member(archive: Path, member: str, dest: Path) -> None:
    """Extract one named regular file from a .tar.gz without trusting archive paths."""
    with tarfile.open(archive, "r:gz") as tar:
        info = next((m for m in tar.getmembers() if Path(m.name).name == member), None)
        if info is None or not info.isfile():
            raise FileNotFoundError(f"{member} not found in {archive.name}")
        src = tar.extractfile(info)
        if src is None:
            raise FileNotFoundError(f"{member} not readable in {archive.name}")
        part = dest.with_name(dest.name + ".part")
        with src, part.open("wb") as out:
            shutil.copyfileobj(src, out, CHUNK)
        part.replace(dest)


def manual_instructions(name: str, src: Source, out_dir: Path, flag: str) -> None:
    """Explain how to fetch ``src`` by hand and use the ``file:`` option."""
    print(
        f"\n  !! Could not download '{name}'. Fetch it manually:\n"
        f"     1. Open {src.url} in a browser (or another mirror of the same file).\n"
        f"     2. Save it as {out_dir / src.filename}\n"
        f"        (or anywhere, then pass {flag} file:<path>).\n"
        f"     3. Re-run this script; files already present are skipped.\n"
        f"     Content: {src.note}",
        file=sys.stderr,
    )


def fetch(choice: str, sources: dict[str, Source], out_dir: Path, flag: str) -> Path | None:
    """Resolve one ``--passwords`` / ``--usernames`` choice to a local file (or ``None``)."""
    if choice == "none":
        return None
    if choice.startswith("file:"):
        path = Path(choice[5:]).expanduser().resolve()
        if not path.is_file():
            print(f"  !! {path} does not exist", file=sys.stderr)
            return None
        print(f"[{flag}] using local file")
        report(path)
        return path

    src = sources[choice]
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / src.filename
    final = out_dir / src.extract if src.extract else archive
    print(f"[{flag}] {choice}: {src.note}")
    if final.is_file() and final.stat().st_size > 0:
        print("  already present, skipping download")
    else:
        if not (archive.is_file() and archive.stat().st_size > 0):
            print(f"  downloading {src.url}")
            try:
                download(src.url, archive)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                print(f"  !! download failed: {exc}", file=sys.stderr)
                manual_instructions(choice, src, out_dir, flag)
                return None
        if src.extract:
            print(f"  extracting {src.extract}")
            try:
                extract_member(archive, src.extract, final)
            except (tarfile.TarError, OSError) as exc:
                print(f"  !! extraction failed: {exc}", file=sys.stderr)
                manual_instructions(choice, src, out_dir, flag)
                return None
            report(archive)
    report(final)
    return final


def _choice(sources: dict[str, Source]) -> Callable[[str], str]:
    def parse(value: str) -> str:
        if value == "none" or value in sources or (value.startswith("file:") and len(value) > 5):
            return value
        raise argparse.ArgumentTypeError(f"expected one of {', '.join(sources)}, none, file:PATH")

    return parse


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 if every requested file is available, else 1."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--passwords",
        type=_choice(PASSWORD_SOURCES),
        default="rockyou-withcount",
        help="rockyou-withcount (preferred) | seclists-rockyou | file:PATH | none",
    )
    ap.add_argument(
        "--usernames",
        type=_choice(USERNAME_SOURCES),
        default="seclists-xato",
        help="seclists-xato | file:PATH | none",
    )
    ap.add_argument("--out", default="data/raw", help="output dir, relative to the repo root")
    args = ap.parse_args(argv)

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir
    ok = True
    for choice, sources, flag in (
        (args.passwords, PASSWORD_SOURCES, "--passwords"),
        (args.usernames, USERNAME_SOURCES, "--usernames"),
    ):
        if choice != "none" and fetch(choice, sources, out_dir, flag) is None:
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
