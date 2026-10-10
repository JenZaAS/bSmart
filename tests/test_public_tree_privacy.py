"""Fail when the public tree contains a known private deployment token.

Digests and the scanner live in tests/private_tokens.py. No file is exempt.
Failure text includes the path and digest, not the matched text.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
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


def iter_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


class PublicTreePrivacyTests(unittest.TestCase):
    def test_forbidden_list_is_hashes_only(self):
        digests = _TOKENS.PRIVATE_TOKEN_DIGESTS
        self.assertGreaterEqual(len(digests), 1)
        for digest in digests:
            self.assertEqual(len(digest), 64)
            int(digest, 16)

    def test_scanner_emits_words_joined_pairs_and_path_prefixes(self):
        found = set(_TOKENS.token_candidates("Alpha Beta /opt/example/child"))
        self.assertIn("alpha", found)
        self.assertIn("alphabeta", found)
        self.assertIn("/opt/example", found)
        self.assertIn("/opt/example/child", found)

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
