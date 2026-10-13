import subprocess
from pathlib import Path

from scripts.build_attack_wordlist import (
    build_wordlist,
    load_base_words,
    mangle,
)


def test_load_base_words_plain_and_count(tmp_path: Path):
    content = "password\n   12345 123456\n1 admin\nqwerty\n"
    p = tmp_path / "words.txt"
    p.write_text(content, encoding="latin-1")
    words = load_base_words(str(p))
    assert words == ["password", "123456", "admin", "qwerty"]


def test_load_base_words_latin1(tmp_path: Path):
    # latin-1 char not in UTF-8
    p = tmp_path / "words.txt"
    p.write_bytes(
        b"hello\xe9world\n"
    )  # printable? e9 is 233, so it's > 0x7E, it should be filtered out
    words = load_base_words(str(p))
    assert words == []

    # Test latin-1 read success with printable chars
    p.write_bytes(b"hello\n")
    words = load_base_words(str(p))
    assert words == ["hello"]


def test_load_base_words_filters(tmp_path: Path):
    content = "".join(
        [
            "\n",  # Empty line
            "   \n",  # Whitespace line (will be stripped to empty by rstrip, then ignored)
            "a" * 33 + "\n",  # > 32 chars
            "\n",
            "a\n",  # 1 char (kept)
            "hello\x7f\n",  # Non-printable
            "   2 invalid\x01\n",  # Non-printable in count format
            "validpass\n",
        ]
    )
    p = tmp_path / "words.txt"
    p.write_text(content, encoding="latin-1")
    words = load_base_words(str(p))
    # '   \n' after rstrip is '' -> skipped.
    assert words == ["a", "validpass"]


def test_mangle():
    variants = mangle("password")

    assert "password" in variants  # 8. original
    assert "Password" in variants  # 9. capitalized
    assert "p@$$w0rd" in variants  # 10. leet (a->@, s->$, o->0)
    assert "password1" in variants  # 11. +1
    assert "password123" in variants  # 12. +123
    assert "password!" in variants  # 13. +!
    # 14. 2020-2026
    for year in range(2020, 2027):
        assert f"password{year}" in variants

    # 15. deterministic
    assert mangle("password") == mangle("password")


def test_build_wordlist_order_and_duplicates():
    # base words
    bases = ["hello", "hello", "Hello"]
    result = build_wordlist(bases, top=3, max_total=100)

    # 16. removes duplicates
    # "hello" has variants including "Hello" (capitalized).
    # The second "hello" will produce duplicates which should be ignored.
    # The third "Hello" will also produce duplicates.
    assert len(result) == len(set(result))

    # 17. preserves order
    # The first element should be the first variant of the first base, which is "hello".
    assert result[0] == "hello"
    assert result[1] == "Hello"


def test_build_wordlist_limits():
    # 18. top limit works
    bases = ["a", "b", "c", "d"]
    # 13 variants per word
    result = build_wordlist(bases, top=2, max_total=100)
    assert len(result) == 25

    # 19. max_total limit works
    result2 = build_wordlist(bases, top=4, max_total=30)
    assert len(result2) == 30


def test_build_wordlist_zero_limits():
    assert build_wordlist(["a"], top=0, max_total=10) == []
    assert build_wordlist(["a"], top=10, max_total=0) == []


def test_cli_fallback_and_args(tmp_path: Path):
    out_file = tmp_path / "out.txt"
    # 20. Built-in BASE_WORDS fallback works
    # 21. CLI creates the requested output file
    # 23. CLI respects --top
    # 24. CLI respects --max-total

    cmd = [
        "python",
        "-m",
        "scripts.build_attack_wordlist",
        "--top",
        "2",
        "--max-total",
        "20",
        "--out",
        str(out_file),
    ]

    subprocess.run(cmd, check=True)  # noqa: S603

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    lines = content.splitlines()

    # 22. one word per line
    # Since we maxed at 20, we should have exactly 20 lines.
    assert len(lines) == 20

    # Verify it used the built-in bases ("password", "123456"...)
    assert lines[0] == "password"


def test_cli_custom_input(tmp_path: Path):
    in_file = tmp_path / "in.txt"
    in_file.write_text("custompass\n", encoding="latin-1")
    out_file = tmp_path / "out.txt"

    cmd = [
        "python",
        "-m",
        "scripts.build_attack_wordlist",
        "--input",
        str(in_file),
        "--out",
        str(out_file),
    ]

    subprocess.run(cmd, check=True)  # noqa: S603
    assert out_file.exists()

    # "custompass" gives 13 variants
    lines = out_file.read_text().splitlines()
    assert len(lines) == 13
    assert lines[0] == "custompass"


def test_cli_deterministic(tmp_path: Path):
    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"

    cmd1 = ["python", "-m", "scripts.build_attack_wordlist", "--out", str(out1)]
    cmd2 = ["python", "-m", "scripts.build_attack_wordlist", "--out", str(out2)]

    subprocess.run(cmd1, check=True)  # noqa: S603
    subprocess.run(cmd2, check=True)  # noqa: S603

    assert out1.read_text() == out2.read_text()
