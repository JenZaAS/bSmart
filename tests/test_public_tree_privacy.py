"""Fail when the public tree contains a known private deployment token.

Digests and the scanner live in tests/private_tokens.py. No file is exempt.
Failure text includes the path and digest, not the matched text.
"""

from __future__ import annotations

import hashlib
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


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Made-up names. The real digest list is used only by the tree scan.
_EXAMPLE_DIGESTS = frozenset(
    {
        _digest("acmecorp"),
        _digest("acme/share"),
        _digest("acmecorpltd"),
    }
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

    def _example_hits(self, text: str, public_compounds: frozenset[str] | set[str] | None = None):
        return _TOKENS.private_digest_hits(text, _EXAMPLE_DIGESTS, public_compounds)

    def test_synthetic_compounds_paths_and_joined_names_are_caught(self):
        two_word = _digest("acmecorp")
        three_word = _digest("acmecorpltd")
        share = _digest("acme/share")
        self.assertIn(two_word, self._example_hits("AcmeCorpAdmin"))
        self.assertIn(two_word, self._example_hits("acmecorp2"))
        self.assertIn(two_word, self._example_hits("Acme Corp"))
        self.assertNotIn(three_word, self._example_hits("Acme Corp"))
        self.assertIn(three_word, self._example_hits("Acme Corp Ltd"))
        self.assertIn(two_word, self._example_hits("acme-corp"))
        self.assertIn(two_word, self._example_hits("acme_corp"))
        self.assertEqual(self._example_hits(r"E:\acme\share"), [share])
        self.assertIn(share, self._example_hits(r"E:\acme\share\data"))

    def test_ordinary_words_are_not_synthetic_matches(self):
        for text in (
            "digital",
            "configuration",
            "corporate",
            "DigitalSignal",
            "ThreadPool",
            "acme",
            "share",
            "One Two Three",
            r"E:\other\place",
        ):
            self.assertEqual(self._example_hits(text), [], text)

    def test_org_allow_list_skips_only_that_compound(self):
        allowed = frozenset({"acmecorpas"})
        self.assertEqual(self._example_hits("AcmeCorpAS", allowed), [])
        self.assertIn(_digest("acmecorp"), self._example_hits("AcmeCorpAS", frozenset()))
        self.assertIn(_digest("acmecorp"), self._example_hits("AcmeCorpAdmin", allowed))

    def test_non_utf8_file_is_decoded_and_scanned(self):
        blob = b"\xff" + b"acmecorp" + b"\xfe"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            path.write_bytes(blob)
            text = read_repo_text(path)
        self.assertIsNotNone(text)
        self.assertIn(_digest("acmecorp"), self._example_hits(text or ""))

    def test_rule_checks_do_not_use_the_real_digest_list(self):
        self.assertTrue(_EXAMPLE_DIGESTS.isdisjoint(_TOKENS.PRIVATE_TOKEN_DIGESTS))

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
