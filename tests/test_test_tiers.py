"""bTestTiers: manifest, reports, instance history, run log, tier moves, due check."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bTestTiers"


def load_module():
    path = ROOT / "scripts" / "bsmart_test_tiers.py"
    spec = importlib.util.spec_from_file_location("bsmart_test_tiers_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tt = load_module()

JUNIT = """<?xml version="1.0"?>
<testsuites><testsuite name="s">
 <testcase classname="tests.test_a" file="./tests/test_a.py" name="saves a file [main/high fix #37]" time="0.1"/>
 <testcase classname="tests.test_a" file="tests/test_a.py" name="odd unicode name" time="3.5"/>
 <testcase classname="tests.test_b" file="tests/test_b.py" name="label text" time="0.2"><failure message="x"/></testcase>
 <testcase classname="tests.test_b" file="tests/test_b.py" name="skipped one" time="0"><skipped/></testcase>
</testsuite></testsuites>
"""

MANIFEST = """# comment
normal   main/high  #37  tests/test_a.py::saves a file
normal   edge/med   -    tests/test_a.py::odd unicode name
special  main/low   -    tests/test_b.py::*
"""


def results(ids, result="pass", seconds=0.1):
    return {i: {"result": result, "seconds": seconds} for i in ids}


class TestTiers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.settings = dict(tt.DEFAULTS)

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                              encoding="utf-8", cwd=self.dir)

    def write(self, name, text):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_junit_ids_strip_inline_tags_and_read_results(self):
        r = tt.read_reports([self.write("r.xml", JUNIT)])
        self.assertEqual(r["tests/test_a.py::saves a file"]["result"], "pass")
        self.assertEqual(r["tests/test_b.py::label text"]["result"], "fail")
        self.assertEqual(r["tests/test_b.py::skipped one"]["result"], "skip")
        self.assertEqual(r["tests/test_a.py::odd unicode name"]["seconds"], 3.5)

    def test_json_report(self):
        r = tt.read_reports([self.write("r.json", json.dumps([{"id": "m/t::x [edge/low]", "result": "fail"}]))])
        self.assertEqual(r, {"m/t::x": {"result": "fail", "seconds": 0.0, "raw_name": "m/t::x [edge/low]"}})

    def test_lookup_exact_wins_over_glob(self):
        entries, problems = tt.parse_manifest(MANIFEST + "normal main/med - tests/test_b.py::label text\n")
        self.assertEqual(problems, [])
        self.assertEqual(tt.lookup(entries, "tests/test_b.py::label text").tag, "main/med")
        self.assertEqual(tt.lookup(entries, "tests/test_b.py::other").tag, "main/low")
        self.assertIsNone(tt.lookup(entries, "tests/test_c.py::x"))

    def test_check_flags_untagged_bad_and_protected_in_special(self):
        m = self.write("m.txt", "normal ?/? - a::x\nspecial main/high - a::y\nnormal main/huge - a::z\nspecial edge/low #5 a::w\n")
        out = self.cli("check", "--manifest", str(m))
        self.assertEqual(out.returncode, 1, out.stderr)
        for word in ("untagged: a::x", "protected_in_special: a::y", "bad_tag", "protected_in_special: a::w"):
            self.assertIn(word, out.stdout)

    def test_init_then_check_clean_after_tagging(self):
        rep = self.write("r.xml", JUNIT)
        m = self.dir / "test-tiers.txt"
        self.assertEqual(self.cli("init", "--manifest", str(m), "--report", str(rep)).returncode, 0)
        text = m.read_text(encoding="utf-8")
        self.assertIn("main/high  #37      tests/test_a.py::saves a file", text)
        self.assertIn("?/?", text)
        self.assertEqual(self.cli("check", "--manifest", str(m)).returncode, 1)
        m.write_text(MANIFEST, encoding="utf-8")
        out = self.cli("check", "--manifest", str(m), "--report", str(rep))
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_place_by_tags_and_time(self):
        entries, _ = tt.parse_manifest(MANIFEST.replace("special", "normal") + "normal edge/high - x::h\nnormal main/med - x::m\n")
        tt.place(entries, tt.read_reports([self.write("r.xml", JUNIT)]), self.settings)
        tiers = {e.pattern: e.tier for e in entries}
        self.assertEqual(tiers["tests/test_a.py::saves a file"], "normal")       # high + fix
        self.assertEqual(tiers["tests/test_a.py::odd unicode name"], "special")  # edge, slow
        self.assertEqual(tiers["tests/test_b.py::*"], "special")                 # low
        self.assertEqual(tiers["x::h"], "normal")                                # high stays
        self.assertEqual(tiers["x::m"], "normal")

    def test_demote_after_streak_and_weeks_never_high_or_fix(self):
        entries, _ = tt.parse_manifest("normal main/med - a::m\nnormal main/high - a::h\nnormal main/med #9 a::f\n")
        s = dict(self.settings, demote_after_runs=3, demote_after_weeks=2)
        start = dt.date(2026, 1, 1)
        for i in range(3):
            tt.record_run(self.dir, results(["a::m", "a::h", "a::f"]), "normal", f"s{i}", "main", s,
                          when=start + dt.timedelta(days=7 * i))
        hist = tt.load_history(self.dir)
        self.assertEqual(tt.review(entries, hist, s, when=start + dt.timedelta(days=13))["to_special"], [])
        moves = tt.review(entries, hist, s, when=start + dt.timedelta(days=14))
        self.assertEqual(moves["to_special"], ["a::m"])
        self.assertEqual({e.pattern: e.tier for e in tt.apply_moves(entries, moves)}["a::m"], "special")

    def test_failed_special_goes_back_and_glob_gets_exact_line(self):
        entries, _ = tt.parse_manifest("special edge/low - a::*\n")
        tt.record_run(self.dir, {**results(["a::x"], "fail"), **results(["a::y"])}, "special", "s1", "main", self.settings)
        moves = tt.review(entries, tt.load_history(self.dir), self.settings)
        self.assertEqual(moves["to_normal"], ["a::x"])
        new = tt.apply_moves(entries, moves)
        self.assertEqual(tt.lookup(new, "a::x").tier, "normal")
        self.assertEqual(tt.lookup(new, "a::y").tier, "special")

    def test_removal_is_only_suggested(self):
        entries, _ = tt.parse_manifest("special edge/low - a::r\n")
        s = dict(self.settings, retire_after_special_runs=2, retire_after_weeks=1)
        for i in range(2):
            tt.record_run(self.dir, results(["a::r"]), "special", f"s{i}", "main", s, when=dt.date(2026, 1, 1 + 14 * i))
        moves = tt.review(entries, tt.load_history(self.dir), s, when=dt.date(2026, 1, 20))
        self.assertEqual(moves["remove_suggestions"], ["a::r"])
        self.assertEqual([e.pattern for e in tt.apply_moves(entries, moves)], ["a::r"])

    def test_due_only_on_main_when_changed_and_after_interval(self):
        s = self.settings
        self.assertEqual(tt.special_due(self.dir, "a", "feature", s)[0], False)
        self.assertEqual(tt.special_due(self.dir, "a", "main", s)[0], True)
        tt.record_run(self.dir, results(["t"]), "special", "a", "main", s, when=dt.date(2026, 1, 1))
        self.assertFalse(tt.special_due(self.dir, "a", "main", s, when=dt.date(2026, 3, 1))[0])
        self.assertFalse(tt.special_due(self.dir, "b", "main", s, when=dt.date(2026, 1, 10))[0])
        self.assertTrue(tt.special_due(self.dir, "b", "main", s, when=dt.date(2026, 1, 15))[0])
        tt.record_run(self.dir, results(["t"]), "special", "c", "feature", s, when=dt.date(2026, 2, 1))
        self.assertEqual(tt.load_history(self.dir)["last_special"]["sha"], "a")

    def test_run_log_one_file_per_tier_with_key_stats(self):
        s = self.settings
        r1 = tt.record_run(self.dir, {**results(["a::1"]), **results(["a::2"], seconds=5.0)}, "normal", "sha1", "main", s,
                           when=dt.date(2026, 1, 1))
        tt.append_log(self.dir, r1, None, s, when=dt.date(2026, 1, 1))
        r2 = tt.record_run(self.dir, {**results(["a::1"], "fail"), **results(["a::2"])}, "normal", "sha2", "main", s,
                           when=dt.date(2026, 1, 2))
        tt.append_log(self.dir, r2, {"to_normal": [], "to_special": ["a::2"]}, s, when=dt.date(2026, 1, 2))
        r3 = tt.record_run(self.dir, results(["b::1"]), "all", "sha3", "main", s, when=dt.date(2026, 1, 3))
        tt.append_log(self.dir, r3, None, s, when=dt.date(2026, 1, 3))
        self.assertEqual(sorted(p.name for p in self.dir.glob("log-*.md")), ["log-normal.md", "log-special.md"])
        normal = (self.dir / "log-normal.md").read_text(encoding="utf-8")
        self.assertEqual(normal.count("\n- "), 2)
        self.assertIn("- 2026-01-01 sha1 main | 2 pass, 0 fail, 0 skip | 5.1s", normal)
        self.assertIn("slowest: a::2 5.0s", normal)
        self.assertIn("new failures: a::1", normal)
        self.assertIn("to special: 1 (a::2)", normal)
        self.assertIn("(all)", (self.dir / "log-special.md").read_text(encoding="utf-8"))
        # entries past keep_months are dropped on the next write
        r4 = tt.record_run(self.dir, results(["a::1"]), "normal", "sha4", "main", s, when=dt.date(2027, 6, 1))
        tt.append_log(self.dir, r4, None, s, when=dt.date(2027, 6, 1))
        normal = (self.dir / "log-normal.md").read_text(encoding="utf-8")
        self.assertNotIn("sha1", normal)
        self.assertIn("sha4", normal)

    def test_cli_record_review_due_use_instance_state(self):
        content = self.dir / "content"
        rep = self.write("r.xml", JUNIT)
        m = self.write("test-tiers.txt", MANIFEST)
        base = ["--content-root", str(content), "--project", "demo", "--repo", "app"]
        out = self.cli("record", *base, "--report", str(rep), "--tier", "all", "--sha", "abc", "--branch", "main",
                       "--manifest", str(m))
        self.assertEqual(out.returncode, 0, out.stderr)
        store = content / "State" / "test-tiers" / "demo" / "app"
        for name in ("history.json", "runs.jsonl", "log-special.md"):
            self.assertTrue((store / name).is_file(), name)
        self.assertIn("normal   main/low   -        tests/test_b.py::label text", m.read_text(encoding="utf-8"))
        self.assertEqual(self.cli("due", *base, "--sha", "abc", "--branch", "main").returncode, 1)
        out = self.cli("review", *base, "--manifest", str(m), "--out", str(self.dir / "review.md"))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Removal suggestions", (self.dir / "review.md").read_text(encoding="utf-8"))

    def test_default_demotion_is_100_passes_over_4_weeks_and_restarts_after_a_failure(self):
        self.assertEqual((tt.DEFAULTS["demote_after_runs"], tt.DEFAULTS["demote_after_weeks"]), (100, 4))
        entries, _ = tt.parse_manifest("normal main/med - a::m\n")
        s = self.settings
        start = dt.date(2026, 1, 1)
        for i in range(99):
            tt.record_run(self.dir, results(["a::m"]), "normal", f"s{i}", "feature", s, when=start)
        late = start + dt.timedelta(days=40)
        self.assertEqual(tt.review(entries, tt.load_history(self.dir), s, when=late)["to_special"], [])
        tt.record_run(self.dir, results(["a::m"]), "normal", "s99", "feature", s, when=start)
        self.assertEqual(tt.review(entries, tt.load_history(self.dir), s, when=start + dt.timedelta(days=27))["to_special"], [])
        self.assertEqual(tt.review(entries, tt.load_history(self.dir), s, when=start + dt.timedelta(days=28))["to_special"], ["a::m"])
        # a failure in special sends it back and the full streak starts again
        special, _ = tt.parse_manifest("special main/med - a::m\n")
        tt.record_run(self.dir, results(["a::m"], "fail"), "special", "x", "main", s, when=late)
        moves = tt.review(special, tt.load_history(self.dir), s, when=late)
        self.assertEqual(moves["to_normal"], ["a::m"])
        back = tt.apply_moves(special, moves)
        for i in range(99):
            tt.record_run(self.dir, results(["a::m"]), "normal", f"t{i}", "feature", s, when=late)
        self.assertEqual(tt.review(back, tt.load_history(self.dir), s, when=late + dt.timedelta(days=60))["to_special"], [])

    def test_pause_when_main_inactive_then_reactivate_on_new_work(self):
        s = self.settings
        tt.record_run(self.dir, results(["t"]), "all", "m1", "main", s, when=dt.date(2026, 1, 1))
        due, why = tt.special_due(self.dir, "m1", "main", s, when=dt.date(2026, 3, 2))
        self.assertFalse(due)
        self.assertIn("paused (inactive)", why)
        log = (self.dir / "log-special.md").read_text(encoding="utf-8")
        self.assertIn("paused (inactive)", log)
        self.assertEqual(tt.load_history(self.dir)["paused"]["sha"], "m1")
        self.assertIn("paused (inactive)", tt.special_due(self.dir, "m1", "main", s, when=dt.date(2026, 4, 1))[1])
        self.assertEqual(log.count("paused"), (self.dir / "log-special.md").read_text(encoding="utf-8").count("paused"))
        run = tt.record_run(self.dir, results(["t"]), "normal", "m2", "main", s, when=dt.date(2026, 4, 2))
        self.assertTrue(any(n.startswith("re-activated") for n in run["notes"]))
        self.assertIsNone(tt.load_history(self.dir)["paused"])
        self.assertTrue(tt.special_due(self.dir, "m2", "main", s, when=dt.date(2026, 4, 2))[0])
        # an old commit date passed in also pauses
        self.assertIn("paused", tt.special_due(self.dir, "m3", "main", s, when=dt.date(2026, 9, 1),
                                               commit_date="2026-06-01")[1])

    def test_first_record_notes_setup_and_creates_missing_manifest(self):
        content = self.dir / "content"
        rep = self.write("r.xml", JUNIT)
        m = self.dir / "test-tiers.txt"
        out = self.cli("record", "--content-root", str(content), "--project", "demo", "--repo", "app",
                       "--report", str(rep), "--tier", "normal", "--sha", "abc", "--branch", "feature",
                       "--manifest", str(m))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(m.is_file())
        log = (content / "State" / "test-tiers" / "demo" / "app" / "log-normal.md").read_text(encoding="utf-8")
        self.assertIn("note: set up: test tiers history started", log)
        self.assertIn("note: set up: manifest test-tiers.txt created with 4 tests", log)

    def test_gate_blocks_only_normal_failures(self):
        rep = self.write("r.xml", JUNIT)  # test_b label text fails
        m = self.write("m.txt", MANIFEST)  # test_b is special
        out = self.cli("gate", "--manifest", str(m), "--report", str(rep))
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("not blocking (special tier", out.stdout)
        m.write_text(MANIFEST.replace("special  main/low", "normal   main/low"), encoding="utf-8")
        out = self.cli("gate", "--manifest", str(m), "--report", str(rep))
        self.assertEqual(out.returncode, 1)
        self.assertIn("blocking (normal tier): tests/test_b.py::label text", out.stdout)

    def test_issue_body_and_link_note(self):
        content = self.dir / "content"
        rep = self.write("r.xml", JUNIT)
        m = self.write("test-tiers.txt", MANIFEST)
        base = ["--content-root", str(content), "--project", "demo", "--repo", "app"]
        out = self.cli("record", *base, "--report", str(rep), "--tier", "special", "--sha", "abcdef123456",
                       "--branch", "main")
        self.assertIn("open an issue", out.stdout)
        out = self.cli("issue", *base, "--manifest", str(m))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Special-tier test failures on main at abcdef1234", out.stdout)
        self.assertIn("| `tests/test_b.py::label text` | main/low |", out.stdout)
        self.assertIn("does not block", out.stdout)
        self.assertEqual(self.cli("note", *base, "--tier", "special", "--text", "issue: #123").returncode, 0)
        log = (content / "State" / "test-tiers" / "demo" / "app" / "log-special.md").read_text(encoding="utf-8")
        self.assertTrue(log.rstrip().endswith("note: issue: #123"))

    def test_settings_project_override(self):
        p = self.dir / "State" / "test-tiers" / "settings.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"special_every_days": 7, "projects": {"demo": {"slow_seconds": 5}}}), encoding="utf-8")
        s = tt.load_settings(self.dir, "demo")
        self.assertEqual((s["special_every_days"], s["slow_seconds"], s["demote_after_runs"]), (7, 5, 100))

    def test_templates_are_blank_and_load(self):
        entries, problems = tt.parse_manifest((ROOT / "bSmart_Templates" / "test-tiers.template.txt").read_text(encoding="utf-8"))
        self.assertEqual((entries, problems), ([], []))
        data = json.loads((ROOT / "bSmart_Templates" / "test-tiers-settings.template.json").read_text(encoding="utf-8"))
        self.assertEqual({k: data[k] for k in tt.DEFAULTS}, {k: (float(v) if k == "slow_seconds" else v)
                                                             for k, v in tt.DEFAULTS.items()})
        self.assertEqual(data["projects"], {})
        self.assertTrue((ROOT / "bSmart_Templates" / "test-tiers-log.template.md").is_file())

    def test_protocol_is_indexed_and_pointed_to(self):
        self.assertIn("test-tiers.md", (ROOT / "bSmart_Protocols" / "protocols.md").read_text(encoding="utf-8"))
        self.assertIn("test-tiers.md", (ROOT / "bSmart_Map.md").read_text(encoding="utf-8"))
        for rel in ("bSmart_Protocols/design-context.md", "bSmart-Extensions/bCritic/critic.md",
                    "bSmart-Extensions/bArchitect/architect.md", "bSmart-Extensions/bCoder/coder.md",
                    "bSmart-Extensions/bSwarm/bswarm-protocol.md"):
            self.assertIn("test-tiers.md", (ROOT / rel).read_text(encoding="utf-8"), rel)


if __name__ == "__main__":
    unittest.main()
