"""bMap lint, status, and map finding (bSmart-Extensions/bMap/bmap.py)."""
from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import io
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BMAP_DIR = ROOT / "bSmart-Extensions" / "bMap"
BASK_DIR = ROOT / "bSmart-Extensions" / "bAsk"


def _load():
    loader = importlib.machinery.SourceFileLoader("bsmart_bmap_ext", str(BMAP_DIR / "bmap.py"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[loader.name] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


bmap = _load()
NOW = datetime(2026, 1, 31, 12, 0, tzinfo=timezone.utc)

MAP = """---
slug: {slug}
tracker: local
---

# Example map

## Destination

A locked decision on how exports work.

## Notes

{notes}

## Decisions so far

{decisions}

## Not yet specified

{fog}

## Out of scope

{scoped}
"""


def ticket(type_="explore", blocked_by="[]", claimed_by="", claimed_at="", decided_by="",
           title="Which format do exports use?", tail="", extra=""):
    return (
        f"---\ntype: {type_}\nblocked_by: {blocked_by}\nclaimed_by: {claimed_by}\n"
        f"claimed_at: {claimed_at}\ndecided_by: {decided_by}\n{extra}---\n\n"
        f"# {title}\n\n## Question\n\nWhat should it be?\n{tail}"
    )


ANSWER = "\n## Answer\n\nCSV first.\n"


class MapFixture:
    def __init__(self, tmp: Path, slug="exports", notes="Plain words.", decisions="", fog="", scoped=""):
        self.root = tmp / slug
        (self.root / "tickets").mkdir(parents=True)
        (self.root / "map.md").write_text(
            MAP.format(slug=slug, notes=notes, decisions=decisions, fog=fog, scoped=scoped), encoding="utf-8"
        )

    def add(self, name: str, text: str) -> None:
        (self.root / "tickets" / name).write_text(text, encoding="utf-8")

    def lint(self, **kwargs):
        return bmap.lint_map(bmap.load_map(self.root), now=NOW, **kwargs)


def errors(diags):
    return [d.message for d in diags if d.level == "error"]


def warns(diags):
    return [d.message for d in diags if d.level == "warn"]


class BMapLintTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_clean_map_has_no_findings(self):
        m = MapFixture(self.tmp, decisions="- [Format](./tickets/01-format.md): CSV first.")
        m.add("01-format.md", ticket(decided_by="operator", tail=ANSWER))
        m.add("02-columns.md", ticket(blocked_by="[01]", title="Which columns?"))
        self.assertEqual(m.lint(), [])
        data = bmap.load_map(m.root)
        self.assertEqual([t.num for t in bmap.frontier(data)], [2])

    def test_status_is_derived_and_fences_are_not_structure(self):
        m = MapFixture(self.tmp)
        m.add("01-a.md", ticket(tail="\n```\n## Answer\n\nquoted\n```\n"))
        m.add("02-b.md", ticket(title="B?", claimed_by="s1", claimed_at="2026-01-31T09:00:00Z", tail="\n## Answer\n\n"))
        data = bmap.load_map(m.root)
        self.assertEqual(data.by_num(1).status, "open")
        self.assertEqual(data.by_num(2).status, "claimed")
        self.assertTrue(any("empty '## Answer'" in e for e in errors(m.lint())))

    def test_stored_status_that_disagrees_is_an_error(self):
        m = MapFixture(self.tmp)
        m.add("01-a.md", ticket(extra="status: resolved\n"))
        self.assertTrue(any("disagrees" in e for e in errors(m.lint())))

    def test_graph_errors(self):
        m = MapFixture(self.tmp)
        m.add("01-a.md", ticket(blocked_by="[02]", title="A?"))
        m.add("02-b.md", ticket(blocked_by="[01]", title="B?"))
        m.add("03-c.md", ticket(blocked_by="[03, 09]", title="C?"))
        found = errors(m.lint())
        self.assertTrue(any("cycle" in e for e in found))
        self.assertIn("blocked_by itself", found)
        self.assertTrue(any("09, which does not exist" in e for e in found))

    def test_claims(self):
        m = MapFixture(self.tmp)
        m.add("01-a.md", ticket(claimed_by="s1", claimed_at="2026-01-27T09:00:00Z", title="A?"))
        m.add("02-b.md", ticket(claimed_by="s2", claimed_at="2026-01-31T09:00:00Z", title="B?"))
        m.add("03-c.md", ticket(claimed_by="s3", claimed_at="yesterday", title="C?"))
        diags = m.lint()
        self.assertTrue(any("over 72h" in w for w in warns(diags)))
        self.assertEqual(sum("over 72h" in w for w in warns(diags)), 1)
        self.assertTrue(any("one ticket per session" in w for w in warns(diags)))
        self.assertTrue(any("not an ISO 8601" in e for e in errors(diags)))

    def test_index_must_match_tickets(self):
        m = MapFixture(self.tmp, decisions="- [B](./tickets/02-b.md): not yet.", scoped="")
        m.add("01-a.md", ticket(decided_by="operator", tail=ANSWER, title="A?"))
        m.add("02-b.md", ticket(title="B?"))
        m.add("03-c.md", ticket(title="C?", tail="\n## Ruled out\n\nPast the destination.\n"))
        found = errors(m.lint())
        self.assertTrue(any("missing from the map's Decisions so far" in e for e in found))
        self.assertTrue(any("which is open, not resolved" in e for e in found))
        self.assertTrue(any("missing from the map's Out of scope" in e for e in found))

    def test_human_decides_explore_and_prototype(self):
        m = MapFixture(self.tmp, decisions="- [A](./tickets/01-a.md): x\n- [B](./tickets/02-b.md): y\n- [C](./tickets/03-c.md): z")
        m.add("01-a.md", ticket(tail=ANSWER, title="A?"))
        m.add("02-b.md", ticket(type_="prototype", tail=ANSWER, title="B?"))
        m.add("03-c.md", ticket(type_="research", tail=ANSWER, title="C?"))
        found = [e for e in errors(m.lint()) if "decided_by" in e]
        self.assertEqual(len(found), 2)

    def test_map_cannot_switch_off_no_build_rule(self):
        m = MapFixture(self.tmp, notes="This map carries execution.")
        self.assertTrue(any("only the human" in e for e in errors(m.lint())))
        other = MapFixture(self.tmp, slug="other")
        text = (other.root / "map.md").read_text(encoding="utf-8").replace("tracker: local", "tracker: local\nbuild_allowed: yes")
        (other.root / "map.md").write_text(text, encoding="utf-8")
        self.assertTrue(any("build_allowed" in e for e in errors(other.lint())))

    def test_map_size_limit(self):
        m = MapFixture(self.tmp)
        for n in range(1, 11):
            m.add(f"{n:02d}-t.md", ticket(title=f"Q{n}?"))
        self.assertTrue(any("near the limit" in w for w in warns(m.lint())))
        for n in range(11, 14):
            m.add(f"{n:02d}-t.md", ticket(title=f"Q{n}?"))
        self.assertTrue(any("over the limit of 12" in e for e in errors(m.lint())))

    def test_fog_and_types(self):
        fog = "- **Which columns?** Later. <clears-with: 01>\n- **Ordering.** <clears-with: 07>"
        m = MapFixture(self.tmp, fog=fog, decisions="- [A](./tickets/01-a.md): x")
        m.add("01-a.md", ticket(type_="grilling", decided_by="operator", tail=ANSWER, title="A?"))
        m.add("02-b.md", ticket(title="Which columns?"))
        m.add("03-c.md", ticket(type_="build", title="C?"))
        m.add("04-d.md", ticket(type_="task", title="Implement the exporter"))
        m.add("05-e.md", ticket(type_="discussion", title="E?"))
        diags = m.lint()
        found = errors(diags)
        self.assertTrue(any("duplicates a live ticket" in e for e in found))
        self.assertTrue(any("already resolved" in e for e in found))
        self.assertTrue(any("07, which does not exist" in e for e in found))
        self.assertTrue(any("'build' is not one of" in e for e in found))
        self.assertTrue(any("'grilling' is an old name; write 'explore'" in e for e in found))
        self.assertTrue(any("'discussion' is an old name; write 'explore'" in e for e in found))
        self.assertTrue(any("build step" in w for w in warns(diags)))

    def test_slug_must_match_folder(self):
        m = MapFixture(self.tmp)
        text = (m.root / "map.md").read_text(encoding="utf-8").replace("slug: exports", "slug: other")
        (m.root / "map.md").write_text(text, encoding="utf-8")
        self.assertTrue(any("does not match the folder" in e for e in errors(m.lint())))


REGISTRY = """# Map registry

| slug | destination | status | last worked | aliases |
|---|---|---|---|---|
{rows}
"""


class BMapRegistryAndFindTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def rows(self, text):
        return bmap.parse_registry(REGISTRY.format(rows=text))

    def test_registry_lint(self):
        MapFixture(self.tmp, slug="exports")
        MapFixture(self.tmp, slug="orphan")
        rows = (
            "| exports | Export decision | active | 2026-01-30 | csv |\n"
            "| ghost | Nothing | sleeping | someday | csv |"
        )
        (self.tmp / "REGISTRY.md").write_text(REGISTRY.format(rows=rows), encoding="utf-8")
        found = errors(bmap.lint_registry(self.tmp))
        self.assertTrue(any("'csv' is used twice" in e for e in found))
        self.assertTrue(any("sleeping" in e for e in found))
        self.assertTrue(any("someday" in e for e in found))
        self.assertTrue(any("ghost: no ghost/map.md" in e for e in found))
        self.assertTrue(any("'orphan' is missing" in e for e in found))

    def test_template_rows_are_ignored(self):
        text = (BMAP_DIR / "templates" / "registry.template.md").read_text(encoding="utf-8")
        self.assertEqual(bmap.parse_registry(text), [])

    def test_find_order(self):
        rows = self.rows(
            "| exports | Decide the CSV export format | active | 2026-01-30 | csv |\n"
            "| billing | Plan the invoice rewrite | active | 2026-01-20 | - |\n"
            "| search | Plan search ranking | paused | 2026-01-25 | - |\n"
            "| old | Old onboarding plan | done | 2025-12-01 | - |"
        )
        self.assertEqual(bmap.find_map(rows, slug="csv").slug, "exports")
        missing = bmap.find_map(rows, slug="nope")
        self.assertEqual(missing.result, "ask")
        self.assertEqual(missing.candidates, ["exports", "search", "billing"])
        self.assertEqual(bmap.find_map(rows).result, "ask")
        self.assertEqual(bmap.find_map(rows, ["invoice"]).slug, "billing")
        tie = bmap.find_map(rows, ["plan"])  # stopword: no usable words
        self.assertEqual(tie.result, "ask")
        recent = bmap.find_map(rows, ["rewrite", "ranking"])
        self.assertEqual((recent.result, recent.slug), ("found", "search"))
        self.assertEqual(bmap.find_map(rows, ["weather"]).result, "ask")

    def test_single_active_map_is_used(self):
        rows = self.rows(
            "| exports | Decide the CSV export format | active | 2026-01-30 | - |\n"
            "| search | Plan search ranking | paused | 2026-01-25 | - |"
        )
        self.assertEqual(bmap.find_map(rows).slug, "exports")
        self.assertEqual(bmap.find_map(rows, ["export"]).slug, "exports")
        self.assertEqual(bmap.find_map(rows, ["ranking"]).slug, "search")

    def test_equal_matches_on_same_day_ask(self):
        rows = self.rows(
            "| a-plan | Shared words here | active | 2026-01-30 | - |\n"
            "| b-plan | Shared words here | active | 2026-01-30 | - |"
        )
        result = bmap.find_map(rows, ["shared"])
        self.assertEqual(result.result, "ask")
        self.assertEqual(sorted(result.candidates), ["a-plan", "b-plan"])


class BMapCliAndFilesTests(unittest.TestCase):
    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bmap.main(list(args))
        return code, out.getvalue()

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            m = MapFixture(root)
            m.add("01-a.md", ticket(title="A?"))
            (root / "REGISTRY.md").write_text(
                REGISTRY.format(rows="| exports | Export decision | active | 2026-01-30 | - |"), encoding="utf-8"
            )
            self.assertEqual(self.run_cli("lint", str(m.root), "--now", "2026-01-31T12:00:00Z")[0], 0)
            self.assertEqual(self.run_cli("lint", str(root), "--now", "2026-01-31T12:00:00Z")[0], 0)
            code, out = self.run_cli("status", str(m.root))
            self.assertEqual(code, 0)
            self.assertIn("01  A?", out)
            code, out = self.run_cli("find", str(root))
            self.assertEqual(code, 0)
            self.assertIn("slug: exports", out)
            self.assertEqual(self.run_cli("lint", str(root / "missing"))[0], 2)
            m.add("02-b.md", ticket(blocked_by="[05]", title="B?"))
            self.assertEqual(self.run_cli("lint", str(m.root))[0], 1)

    def test_shared_files_are_blank_templates(self):
        for rel in ("README.md", "bmap-protocol.md", "trackers.md", "bmap.py",
                    "templates/map.template.md", "templates/ticket.template.md",
                    "templates/registry.template.md"):
            self.assertTrue((BMAP_DIR / rel).is_file(), rel)
        self.assertTrue((BASK_DIR / "interview.md").is_file())
        protocol = (BMAP_DIR / "bmap-protocol.md").read_text(encoding="utf-8")
        self.assertIn("../bAsk/", (BMAP_DIR / "README.md").read_text(encoding="utf-8"))
        for rule in ("Plan, do not build", "Only the human can lift rule 1", "12 tickets",
                     "bmap_maps: project | workstream", "never", "calendar time"):
            self.assertIn(rule, protocol)
        subfolders = {p.name for p in BMAP_DIR.iterdir() if p.is_dir()} - {"__pycache__"}
        self.assertEqual(subfolders, {"templates"})  # rules and blank templates only

    def test_features_registry_lists_both(self):
        features = (ROOT / "bSmart_Features.md").read_text(encoding="utf-8")
        for name in ("bMap", "bAsk"):
            self.assertIn(f"### {name}\n", features)
            self.assertIn(f"python ./scripts/bFeature {name}", features)


if __name__ == "__main__":
    unittest.main()
