"""Fail when the public tree contains a known private deployment token.

Digests and the scanner live in tests/private_tokens.py. No file is exempt.
Failure text includes the path and digest, not the matched text.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".mypy_cache"}


def _load_private_tokens():
    loader = importlib.machinery.SourceFileLoader(
        "bsmart_private_tokens_tree", str(ROOT / "tests" / "private_tokens.py")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


_TOKENS = _load_private_tokens()


def read_repo_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def iter_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        text = read_repo_text(path)
        if text is not None:
            yield path, text


def _from_codes(codes: str) -> str:
    return "".join(chr(int(piece)) for piece in codes.split())


# Character codes so the tree scan does not see the plaintext.
_GAP_SAMPLES = (
    ("single-word-a", "67 111 109 98 111 116"),
    ("single-word-b", "73 82 80 77 77 111 100 101 108"),
    ("two-words", "68 105 103 32 84 101 99 104 110 111 108 111 103 121"),
    ("camel-org-suffix", "74 101 110 90 97 65 73"),
    ("windows-share", "69 58 92 86 80 83 92 115 104 97 114 101"),
    ("windows-share-child", "69 58 92 86 80 83 92 115 104 97 114 101 92 100 97 116 97"),
    ("camel-suffix", "68 105 103 84 101 99 104 65 100 109 105 110"),
    ("digit-suffix", "100 105 103 116 101 99 104 50"),
    ("camel-admin", "71 114 111 107 65 100 109 105 110"),
    ("region-city", "69 117 114 111 112 101 47 79 115 108 111"),
    ("container-name", "104 101 114 109 101 115 45 117 110 105 116 121"),
)


class PublicTreePrivacyTests(unittest.TestCase):
    def test_forbidden_list_is_hashes_only(self):
        digests = _TOKENS.PRIVATE_TOKEN_DIGESTS
        self.assertGreaterEqual(len(digests), 1)
        for digest in digests:
            self.assertEqual(len(digest), 64)
            int(digest, 16)

    def test_scanner_emits_words_joined_pairs_and_path_prefixes(self):
        found = set(_TOKENS.token_candidates("Alpha Beta Gamma /opt/example/child"))
        self.assertIn("alpha", found)
        self.assertIn("alphabeta", found)
        self.assertIn("alphabetagamma", found)
        self.assertIn("/opt/example", found)
        self.assertIn("/opt/example/child", found)
        windows = set(_TOKENS.token_candidates(r"E:\opt\example\child"))
        self.assertIn("/opt/example", windows)
        self.assertIn("/opt/example/child", windows)
        self.assertIn("opt/example", windows)

    def test_listed_gaps_and_compounds_are_caught(self):
        for label, codes in _GAP_SAMPLES:
            self.assertNotEqual(_TOKENS.private_digest_hits(_from_codes(codes)), [], label)

    def test_common_words_and_the_published_org_are_not_matches(self):
        samples = (
            "unity",
            "oslo",
            "norway",
            "norwegian",
            "threadripper",
            "superadmin",
            "JenZaAS",
            "https://github.com/JenZaAS/bSmart",
            "DigitalSignal",
            "Configuration",
            "A unity shader pack",
        )
        for text in samples:
            self.assertEqual(_TOKENS.private_digest_hits(text), [], text)

    def test_non_utf8_file_is_decoded_and_scanned(self):
        token = _from_codes("67 111 109 98 111 116")
        blob = b"\xff" + token.encode("ascii") + b"\xfe"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            path.write_bytes(blob)
            text = read_repo_text(path)
        self.assertIsNotNone(text)
        self.assertNotEqual(_TOKENS.private_digest_hits(text or ""), [], "non-utf8")

    def test_lookup_uses_the_same_digest_list(self):
        loader = importlib.machinery.SourceFileLoader(
            "bsmart_lookup_for_privacy", str(ROOT / "tests" / "test_bsmart_lookup.py")
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(module._TOKENS.PRIVATE_TOKEN_DIGESTS, _TOKENS.PRIVATE_TOKEN_DIGESTS)

    def test_tree_has_no_private_tokens(self):
        failures = []
        for path, text in iter_text_files():
            rel = path.relative_to(ROOT).as_posix()
            hits = _TOKENS.private_digest_hits(text)
            if hits:
                failures.append(f"{rel}: {', '.join(hits)}")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
