from __future__ import annotations

import argparse
import re
from pathlib import Path

BASE_WORDS = (
    "password",
    "123456",
    "12345678",
    "1234",
    "qwerty",
    "12345",
    "dragon",
    "123456789",
    "letmein",
    "admin",
    "1234567",
    "monkey",
    "iloveyou",
    "football",
    "baseball",
    "password123",
    "shadow",
    "mustang",
    "trustno1",
    "superman",
    "123123",
    "654321",
    "master",
    "princess",
    "sunshine",
    "welcome",
    "ninja",
    "secret",
    "hello",
    "charlie",
    "hunter2",
    "spring",
    "summer",
    "autumn",
    "winter",
    "111111",
    "cookie",
    "1234567890",
    "michael",
    "joshua",
    "jennifer",
    "daniel",
    "thomas",
    "computer",
    "iloveu",
    "asdfgh",
    "bacon",
    "god",
    "starwars",
    "angels",
)


def _is_printable_ascii(s: str) -> bool:
    return all(0x20 <= ord(c) <= 0x7E for c in s)


def load_base_words(path: str) -> list[str]:
    """
    Load base words from a text wordlist file.
    Supports both plain 'password' format and 'count password' format.
    Reads using latin-1 encoding, keeps insertion order.
    Only printable ASCII passwords with length between 1 and 32 are retained.
    """
    words = []
    with open(path, encoding="latin-1") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue

            match = re.match(r"^\s*\d+\s+(.+)$", line)
            if match:
                pw = match.group(1)
            else:
                pw = line

            if 1 <= len(pw) <= 32 and _is_printable_ascii(pw):
                words.append(pw)
    return words


def mangle(word: str) -> list[str]:
    """
    Return a deterministic list of password variants for the given word.
    Variants include the original word, capitalized, leet transformation,
    and the word appended with '1', '123', '!', and years 2020-2026.
    """
    variants = [word]

    # Capitalized word
    variants.append(word.capitalize())

    # Leet transformation
    leet = (
        word.replace("a", "@")
        .replace("e", "3")
        .replace("i", "1")
        .replace("o", "0")
        .replace("s", "$")
    )
    variants.append(leet)

    # Append suffixes
    variants.append(word + "1")
    variants.append(word + "123")
    variants.append(word + "!")

    # Append years
    for year in range(2020, 2027):
        variants.append(word + str(year))

    return variants


def build_wordlist(base_words: list[str] | tuple[str, ...], top: int, max_total: int) -> list[str]:
    """
    Build a wordlist taking up to `top` base words, generating mangled variants,
    and returning up to `max_total` deterministic, unique passwords.
    """
    if top <= 0 or max_total <= 0:
        return []

    selected = base_words[:top]
    result = []
    seen = set()

    for base in selected:
        for variant in mangle(base):
            if variant not in seen:
                seen.add(variant)
                result.append(variant)
                if len(result) >= max_total:
                    return result
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Attack Wordlist Builder")
    parser.add_argument("--input", type=str, help="Optional input wordlist path.")
    parser.add_argument("--top", type=int, default=300, help="Max base words to use.")
    parser.add_argument("--max-total", type=int, default=2000, help="Max total words to output.")
    parser.add_argument(
        "--out",
        type=str,
        default="backend/attack/wordlists/demo_wordlist.txt",
        help="Output file path.",
    )
    args = parser.parse_args()

    if args.input:
        base_words = load_base_words(args.input)
    else:
        base_words = BASE_WORDS

    wordlist = build_wordlist(base_words, args.top, args.max_total)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for word in wordlist:
            f.write(f"{word}\n")

    print(f"Written {len(wordlist)} words to {out_path}")


if __name__ == "__main__":
    main()
