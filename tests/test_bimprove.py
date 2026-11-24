"""bImprove (0.1.59): coach loop mechanics, tested with a mock agent CLI (no model calls)."""
from __future__ import annotations

import importlib.util
import json
import re
import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "bSmart-Extensions" / "bImprove"
KIT = ROOT / "tests" / "fixtures" / "bimprove-example"

spec = importlib.util.spec_from_file_location("bimprove", EXT / "bimprove.py")
bi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bi)

FAKE_CLI = textwrap.dedent('''
    import argparse, json, os, sys
    from pathlib import Path
    ap = argparse.ArgumentParser()
    for a in ("--model", "--effort", "--workdir", "--sandbox", "--last"):
        ap.add_argument(a, default="")
    a = ap.parse_args()
    prompt = sys.stdin.read()
    wd = Path(a.workdir)
    cmds, final = [], ""
    def ev(o): print(json.dumps(o))
    def cmd(c): cmds.append(c)
    def write(rel, text):
        p = wd / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")
    def append(rel, line):
        p = wd / rel; p.write_text(p.read_text(encoding="utf-8") + line + "\\n", encoding="utf-8")
    m = a.model
    if os.environ.get("FAKE_ENV_PROBE"):
        Path(os.environ["FAKE_ENV_PROBE"]).write_text(str("OPENAI_API_KEY" in os.environ))
    if m == "worker-blocked":
        sys.stderr.write("ERROR exec_command failed: rejected: blocked by policy\\n")
    if m == "worker-quota":
        ev({"type": "turn.failed", "error": {"message": "You've hit your usage limit."}})
        sys.exit(1)
    if m.startswith("worker"):
        md = wd / "bSmart-System" / "bSmart_Protocols" / "knowledge.md"
        good = m == "worker-good" or (m == "worker-learns" and "MAGIC RULE" in md.read_text(encoding="utf-8"))
        cmd("cat AGENTS.md"); cmd("cat bSmart-System/bSmart_Protocols/knowledge.md")
        if "Find out how" in prompt:
            cmd("cat sources/tidewell-api-guide.md"); cmd("cat sources/harbor-meeting-notes.md")
            if good:
                write("bSmart/Library/tools/tidewell-api/api.md", "# Tidewell API\\n- 120 requests per minute\\n- X-Tide-Key header\\n- after cursor\\nSource: sources/tidewell-api-guide.md\\nDate: 2026-11-24\\n")
                write("bSmart/Library/tools/tidewell-api/index.md", "# tidewell-api\\n- [api](api.md) - basics\\n")
                append("bSmart/Library/tools/index.md", "- [tidewell-api/](tidewell-api/index.md) - Tidewell API")
                write("projects/harbor-app/knowledge/integrations/tidewell-sync.md", "# Sync\\n- /berths only\\n- daily 02:00 for Gullwing Marine\\nSource: meeting notes\\nDate: 2026-11-24\\n")
                write("projects/harbor-app/knowledge/integrations/index.md", "# integrations\\n- [tidewell-sync](tidewell-sync.md) - sync\\n")
                append("projects/harbor-app/knowledge/index.md", "- [integrations/](integrations/index.md) - outside services")
            if m == "worker-leaky":
                write("bSmart/Library/tools/tidewell-api/api.md", "# Tidewell\\nUsed by harbor-app.\\n")
            final = "Use /berths, sync daily at 02:00, limit 120 per minute."
        else:
            if good:
                for f in ("projects/harbor-app/knowledge/index.md", "projects/harbor-app/knowledge/integrations/index.md",
                          "projects/harbor-app/knowledge/integrations/tidewell-sync.md", "bSmart/Library/index.md",
                          "bSmart/Library/tools/index.md", "bSmart/Library/tools/tidewell-api/index.md",
                          "bSmart/Library/tools/tidewell-api/api-basics.md"):
                    cmd("cat " + f)
            else:
                cmd("cat sources/tidewell-api-guide.md"); cmd("cat sources/harbor-meeting-notes.md")
            final = "120 requests per minute; the sync runs daily at 02:00."
    elif m.startswith("coach"):
        cand = wd / "candidate.md"
        if not cand.is_file():
            mds = sorted(p for p in (wd / "files").rglob("*.md"))
            cand = mds[-1] if m != "coach-twofiles" else mds[0]
            if m == "coach-twofiles":
                for f in mds:
                    f.write_text(f.read_text(encoding="utf-8") + "\\nextra\\n", encoding="utf-8")
        text = cand.read_text(encoding="utf-8")
        if m == "coach-ok":
            cand.write_text(text.replace("## Habits", "## Habits\\n\\nMAGIC RULE: save key facts.", 1), encoding="utf-8")
        elif m == "coach-noop":
            n = len(list(wd.parent.iterdir()))
            cand.write_text(text.replace("## Layout", "## Layout\\n\\nUnhelpful line %d." % n, 1), encoding="utf-8")
        elif m == "coach-two":
            cand.write_text("X\\n" + text + "\\nY\\n", encoding="utf-8")
        if os.environ.get("FAKE_TAMPER"):
            Path(os.environ["FAKE_TAMPER"]).write_text("tampered", encoding="utf-8")
        (wd / "reason.txt").write_text("one change", encoding="utf-8")
        final = "done"
    elif m.startswith("checker"):
        final = json.dumps({"judged": {"A9": {"1": "pass", "2": "pass", "3": "pass"}},
                            "md_problem": m != "checker-notmd", "quality_ok": True, "notes": "ok"})
    for i, c in enumerate(cmds):
        ev({"type": "item.completed", "item": {"id": "c%d" % i, "type": "command_execution", "command": "bash -lc '" + c + "'"}})
    ev({"type": "item.completed", "item": {"id": "m", "type": "agent_message", "text": final}})
    ev({"type": "turn.completed", "usage": {"input_tokens": 1000, "cached_input_tokens": 400, "output_tokens": 100}})
    if a.last:
        Path(a.last).write_text(final, encoding="utf-8")
''')


class Env:
    """A temp instance with settings and a fake CLI."""

    def __init__(self, worker="worker-good", coach="coach-ok", checker="checker-x", cap=10_000_000):
        self.tmp = Path(tempfile.mkdtemp(prefix="bimprove-"))
        self.instance = self.tmp / "home"
        state = self.instance / "State"
        state.mkdir(parents=True)
        fake = self.tmp / "fakecli.py"
        fake.write_text(FAKE_CLI, encoding="utf-8")
        settings = json.loads((EXT / "templates" / "bimprove-settings.template.json").read_text(encoding="utf-8"))
        settings["command"] = [sys.executable, str(fake), "--model", "{model}", "--effort", "{effort}",
                               "--workdir", "{workdir}", "--sandbox", "{sandbox}", "--last", "{last_message_file}"]
        settings["token_cap_case"] = cap
        settings["timeout_seconds"] = 60
        (state / "bimprove-settings.json").write_text(json.dumps(settings), encoding="utf-8")
        roles = (ROOT / "bSmart-Extensions/bSwarm/templates/role-models.template.yaml").read_text(encoding="utf-8")
        roles = roles.replace("improve_worker: unset", f"improve_worker: {worker}")
        roles = roles.replace("coach: unset", f"coach: {coach}").replace("checker: unset", f"checker: {checker} high")
        (state / "bswarm-role-models.yaml").write_text(roles, encoding="utf-8")
        (state / "bimprove-denylist.txt").write_text("harbor-app\nGullwing\n", encoding="utf-8")
        self.kit = self.tmp / "kit"
        shutil.copytree(KIT, self.kit)

    def case(self, phase="A", rounds=3, runs=3):
        out = self.tmp / f"case-{phase}"
        code = bi.main(["case", "--kit", str(self.kit), "--phase", phase, "--instance", str(self.instance),
                        "--system", str(ROOT), "--out", str(out), "--runs", str(runs), "--rounds", str(rounds)])
        data = json.loads((out / "case.json").read_text(encoding="utf-8")) if (out / "case.json").is_file() else {}
        return code, data, out

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class ConfigTests(unittest.TestCase):
    def test_role_template_has_no_default_models(self):
        text = (ROOT / "bSmart-Extensions/bSwarm/templates/role-models.template.yaml").read_text(encoding="utf-8")
        for key in ("improve_worker: unset", "coach: unset", "checker: unset"):
            self.assertIn(key, text)

    def test_checker_required_and_distinct(self):
        env = Env(checker="unset")
        try:
            probs = bi.check_settings(bi.load_settings(env.instance))
            self.assertTrue(any(p.startswith("checker") for p in probs))
        finally:
            env.close()
        env = Env(worker="same", checker="same")
        try:
            probs = bi.check_settings(bi.load_settings(env.instance))
            self.assertTrue(any("different model" in p for p in probs))
        finally:
            env.close()
        env = Env()
        try:
            s = bi.load_settings(env.instance)
            self.assertEqual(bi.check_settings(s), [])
            self.assertEqual(s["models"]["checker"], {"model": "checker-x", "effort": "high"})
        finally:
            env.close()

    def test_extension_names_no_models(self):
        for path in EXT.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                text = path.read_text(encoding="utf-8").lower()
                # model ids look like <family>-<version>, e.g. "abc-6.1-xyz"; none may appear
                hits = [m for m in re.findall(r"\b[a-z]{2,8}-\d+(?:\.\d+)*(?:-[a-z]+)?\b", text)
                        if not m.startswith(("utf-", "sha-", "iso-", "rfc-", "adr-", "x-"))]
                self.assertEqual(hits, [], f"{path} looks like it names a model")


class RunAndGradeTests(unittest.TestCase):
    def setUp(self):
        self.env = None

    def tearDown(self):
        if self.env:
            self.env.close()

    def run_phase(self, phase, worker, md=None, runs=2):
        self.env = Env(worker=worker)
        s = bi.load_settings(self.env.instance)
        kit = bi.load_kit(self.env.kit)
        spent = {"total": 0, "runs": 0}
        out = self.env.tmp / "runs"
        res = bi.run_phase(kit, phase, s, ROOT, kit["target_md"], md, out, runs, spent)
        key = bi.read_json(self.env.kit / kit["phases"][phase]["answer_key"])
        terms, allow = bi.load_denylist(s["_denylist"])
        return res, bi.grade_runs(key, res, terms, allow, {"A9": {"1": "pass", "2": "pass"}}), out, spent

    def test_fresh_instance_per_run_and_no_answer_key(self):
        res, _, out, spent = self.run_phase("A", "worker-good")
        self.assertEqual(len(res), 2)
        for n in (1, 2):
            work = out / f"run{n}" / "work"
            self.assertTrue((work / "AGENTS.md").is_file())
            self.assertTrue((work / "bSmart-System/bSmart_Protocols/knowledge.md").is_file())
            self.assertFalse(list(work.rglob("answer-key.json")))
        self.assertEqual(spent["total"], 2 * 1100)

    def test_phase_a_good_passes(self):
        _, g, _, _ = self.run_phase("A", "worker-good")
        self.assertTrue(g["bar_met"], g["marks"])

    def test_phase_a_no_saving_fails_storage_rows(self):
        _, g, _, _ = self.run_phase("A", "worker-bad")
        self.assertFalse(g["row_pass"]["A1"])
        self.assertFalse(g["row_pass"]["A2"])
        self.assertIn("A1", g["confirmed"])

    def test_phase_a_leak_fails(self):
        _, g, _, _ = self.run_phase("A", "worker-leaky")
        self.assertFalse(g["row_pass"]["A5"])

    def test_phase_b_good_and_bad(self):
        _, g, _, _ = self.run_phase("B", "worker-good")
        self.assertTrue(g["bar_met"], g["marks"])
        self.env.close()
        _, g, _, _ = self.run_phase("B", "worker-bad")
        self.assertFalse(g["row_pass"]["B1"])
        self.assertFalse(g["row_pass"]["B3"])
        self.assertTrue(g["row_pass"]["B5"])

    def test_candidate_md_is_swapped_in(self):
        self.env = Env()
        cand = self.env.tmp / "cand.md"
        cand.write_text("MAGIC RULE", encoding="utf-8")
        kit = bi.load_kit(self.env.kit)
        dest = self.env.tmp / "inst"
        bi.make_instance(kit, "B", ROOT, kit["target_md"], cand, dest)
        self.assertEqual((dest / "bSmart-System/bSmart_Protocols/knowledge.md").read_text(), "MAGIC RULE")
        self.assertTrue((dest / "projects/harbor-app/knowledge/integrations/tidewell-sync.md").is_file())
        with self.assertRaises(FileExistsError):
            bi.make_instance(kit, "B", ROOT, kit["target_md"], cand, dest)

    def test_api_keys_are_stripped(self):
        self.env = Env()
        probe = self.env.tmp / "probe.txt"
        os.environ["OPENAI_API_KEY"] = "test-not-a-key"
        os.environ["FAKE_ENV_PROBE"] = str(probe)
        try:
            s = bi.load_settings(self.env.instance)
            bi.call_agent(s, "checker", self.env.tmp, "hi", self.env.tmp / "log", "read-only")
        finally:
            del os.environ["OPENAI_API_KEY"], os.environ["FAKE_ENV_PROBE"]
        self.assertEqual(probe.read_text(), "False")


class GenericCaseTests(unittest.TestCase):
    """A case is just a folder: kit.json (targets, prompt, answer key) + instance/."""

    def make_kit(self, env, targets):
        kit = env.tmp / "tiny"
        (kit / "instance").mkdir(parents=True)
        (kit / "instance" / "AGENTS.md").write_text("Follow bSmart-System.\n", encoding="utf-8")
        (kit / "prompt.md").write_text("What is the limit?\n", encoding="utf-8")
        (kit / "key.json").write_text(json.dumps({"rows": [
            {"id": "T1", "says": "Answer names 120.", "check": "answer_contains", "all": ["120"]},
            {"id": "T2", "says": "Never says 'maybe'.", "check": "answer_excludes", "any": ["maybe"]},
            {"id": "T3", "says": "Learns the rule.", "check": "file_contains", "paths": ["never/*"],
             "contains_all": ["x"]}]}), encoding="utf-8")
        (kit / "kit.json").write_text(json.dumps({"name": "tiny", "targets": targets,
                                                  "prompt": "prompt.md", "answer_key": "key.json"}),
                                      encoding="utf-8")
        return kit

    def test_one_phase_kit_with_two_targets(self):
        env = Env(worker="worker-good", coach="coach-ok")
        try:
            targets = ["bSmart_Protocols/design-context.md", "bSmart_Protocols/knowledge.md"]
            kit = bi.load_kit(self.make_kit(env, targets))
            self.assertEqual(list(kit["phases"]), ["main"])
            self.assertEqual(bi.kit_phase(kit, None), "main")
            out = env.tmp / "case"
            code = bi.main(["case", "--kit", kit["_dir"], "--instance", str(env.instance), "--system", str(ROOT),
                            "--out", str(out), "--runs", "2", "--rounds", "1"])
            data = json.loads((out / "case.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            c1 = data["history"][1]
            self.assertEqual(c1["file"], "bSmart_Protocols/knowledge.md")
            self.assertTrue((out / "candidates/c1/files/bSmart_Protocols/design-context.md").is_file())
            work = out / "c1-runs/run1/work/bSmart-System"
            self.assertIn("MAGIC RULE", (work / "bSmart_Protocols/knowledge.md").read_text(encoding="utf-8"))
            self.assertTrue((work / "bSmart_Protocols/design-context.md").is_file())
            self.assertEqual(c1["marks"]["T1"], ["pass", "pass"])
            self.assertEqual(c1["marks"]["T2"], ["pass", "pass"])
        finally:
            env.close()

    def test_two_files_changed_is_rejected(self):
        env = Env(worker="worker-good", coach="coach-twofiles")
        try:
            kit = self.make_kit(env, ["bSmart_Protocols/design-context.md", "bSmart_Protocols/knowledge.md"])
            out = env.tmp / "case"
            bi.main(["case", "--kit", str(kit), "--instance", str(env.instance), "--system", str(ROOT),
                     "--out", str(out), "--runs", "2", "--rounds", "1"])
            data = json.loads((out / "case.json").read_text(encoding="utf-8"))
            self.assertIn("2 files changed", data["history"][1]["rejected"])
        finally:
            env.close()

    def test_kit_needs_targets_and_roles_can_live_in_settings(self):
        env = Env(checker="unset")
        try:
            kit = self.make_kit(env, [])
            with self.assertRaises(bi.ConfigError):
                bi.load_kit(kit)
            sp = env.instance / "State" / "bimprove-settings.json"
            s = json.loads(sp.read_text(encoding="utf-8"))
            s["roles"] = {"checker": "other-model high"}
            sp.write_text(json.dumps(s), encoding="utf-8")
            loaded = bi.load_settings(env.instance)
            self.assertEqual(loaded["models"]["checker"], {"model": "other-model", "effort": "high"})
            self.assertEqual(bi.check_settings(loaded), [])
        finally:
            env.close()

    def test_file_excludes(self):
        work = Path(tempfile.mkdtemp(prefix="bimprove-fx-"))
        try:
            (work / "plan.md").write_text("Use the Hold. Do not lock.", encoding="utf-8")
            row = {"id": "X", "check": "file_excludes", "paths": ["plan.md"], "any": ["reservation"]}
            run = {"reads": [], "created": ["plan.md"], "modified": []}
            self.assertEqual(bi.grade_row(row, run, work, [], []), "pass")
            row["any"] = ["LOCK"]
            self.assertEqual(bi.grade_row(row, run, work, [], []), "fail")
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_blank_case_template_loads(self):
        kit = bi.load_kit(EXT / "templates" / "case")
        self.assertEqual(list(kit["phases"]), ["main"])
        self.assertEqual(kit["version"], "1")
        key = bi.read_json(EXT / "templates" / "case" / "answer-key.json")
        self.assertEqual({r["check"] for r in key["rows"]}, {"answer_contains", "answer_excludes", "judged"})
        self.assertFalse((EXT / "kits").exists(), "real cases live in the operator's project, not here")

    def test_reads_first_generic_names(self):
        row = {"id": "R", "check": "reads_first", "first": ["docs/adr/*"], "must_see": ["docs/adr/README.md"],
               "before": ["src/*"]}
        run = {"reads": ["docs/adr/README.md", "docs/adr/0007.md", "src/a.py"], "created": [], "modified": []}
        self.assertEqual(bi.grade_row(row, run, Path("."), [], []), "pass")
        run["reads"] = ["src/a.py", "docs/adr/README.md"]
        self.assertEqual(bi.grade_row(row, run, Path("."), [], []), "fail")


class RegressionSuiteTests(unittest.TestCase):
    def regress(self, env, worker, out):
        rm = env.instance / "State" / "bswarm-role-models.yaml"
        text = rm.read_text(encoding="utf-8")
        import re as _re
        rm.write_text(_re.sub(r"improve_worker: \S+", f"improve_worker: {worker}", text), encoding="utf-8")
        return bi.main(["regress", "--kit", str(env.kit), "--phase", "A", "--instance", str(env.instance),
                        "--system", str(ROOT), "--out", str(env.tmp / out), "--runs", "2"])

    def test_rerun_records_and_spots_regressions(self):
        env = Env(worker="worker-good")
        try:
            self.assertEqual(self.regress(env, "worker-good", "r1"), 0)
            self.assertEqual(self.regress(env, "worker-bad", "r2"), bi.EXIT_FINDINGS)
            s = bi.load_settings(env.instance)
            hist = bi.read_history(s)
            self.assertEqual(len(hist), 2)
            self.assertEqual(hist[0]["case"], "knowledge-ab")
            self.assertEqual(hist[0]["case_version"], "1")
            self.assertEqual(hist[0]["models"]["improve_worker"], "worker-good medium")
            self.assertIn("A1", hist[1]["compare"]["regressed"])
            self.assertIn("models changed", hist[1]["compare"]["note"])
            self.assertTrue(str(bi.history_path(s)).startswith(str(env.instance / "State")))
            self.assertFalse((env.tmp / "r2" / "candidates").exists())
            self.assertEqual(self.regress(env, "worker-good", "r3"), 0)
            self.assertIn("A1", bi.read_history(s)[-1]["compare"]["gained"])
        finally:
            env.close()

    def test_stall_limit_lets_the_operator_allow_round_three(self):
        env = Env(worker="worker-bad", coach="coach-noop")
        try:
            out = env.tmp / "case-stall"
            bi.main(["case", "--kit", str(env.kit), "--phase", "A", "--instance", str(env.instance),
                     "--system", str(ROOT), "--out", str(out), "--runs", "2", "--rounds", "3", "--stall-limit", "3"])
            data = json.loads((out / "case.json").read_text(encoding="utf-8"))
            self.assertEqual(len(data["history"]), 4)
            self.assertEqual(data["outcome"], "stop:no_improvement")
        finally:
            env.close()

    def test_case_appends_a_score_record(self):
        env = Env(worker="worker-learns", coach="coach-ok")
        try:
            code, data, out = env.case("A")
            hist = bi.read_history(bi.load_settings(env.instance))
            self.assertEqual(len(hist), 1)
            self.assertEqual(hist[0]["mode"], "case")
            self.assertEqual(hist[0]["outcome"], data["outcome"])
            self.assertEqual(hist[0]["best"]["label"], "c1")
        finally:
            env.close()


class CaseTests(unittest.TestCase):
    def test_baseline_passes_no_teaching(self):
        env = Env(worker="worker-good")
        try:
            code, data, out = env.case("A")
            self.assertEqual(code, 0)
            self.assertEqual(data["outcome"], "stop:baseline_passes")
            self.assertFalse((out / "candidates").exists())
        finally:
            env.close()

    def test_coach_fixes_it(self):
        env = Env(worker="worker-learns", coach="coach-ok")
        try:
            code, data, out = env.case("A")
            self.assertEqual(data["outcome"], "stop:improved", data)
            self.assertEqual(data["best"], "c1")
            self.assertTrue((out / "final" / "side-by-side.html").is_file())
            self.assertTrue((out / "final" / "knowledge.md").read_text(encoding="utf-8").count("MAGIC RULE"))
            self.assertIn("MAGIC RULE", (out / "candidates/c1/candidate.md").read_text(encoding="utf-8"))
            self.assertNotIn("MAGIC RULE", (ROOT / "bSmart_Protocols/knowledge.md").read_text(encoding="utf-8"))
        finally:
            env.close()

    def test_phase_b_candidate_also_reruns_phase_a(self):
        env = Env(worker="worker-learns", coach="coach-ok")
        try:
            _, data, out = env.case("B")
            self.assertEqual(data["outcome"], "stop:improved", data)
            self.assertTrue((out / "c1-regress-A" / "run1" / "run.json").is_file())
        finally:
            env.close()

    def test_stops_after_two_rounds_without_improvement(self):
        env = Env(worker="worker-bad", coach="coach-noop")
        try:
            _, data, _ = env.case("A")
            self.assertEqual(data["outcome"], "stop:no_improvement")
            self.assertEqual(len(data["history"]), 3)
        finally:
            env.close()

    def test_more_than_one_change_is_rejected(self):
        env = Env(worker="worker-bad", coach="coach-two")
        try:
            _, data, _ = env.case("A")
            self.assertIn("rejected", data["history"][1])
            self.assertEqual(data["outcome"], "stop:no_improvement")
        finally:
            env.close()

    def test_not_an_md_problem_from_checker(self):
        env = Env(worker="worker-bad", checker="checker-notmd")
        try:
            _, data, _ = env.case("A")
            self.assertEqual(data["outcome"], "stop:not_an_md_problem")
        finally:
            env.close()

    def test_guard_stops_a_coach_that_edits_the_answer_key(self):
        env = Env(worker="worker-bad", coach="coach-ok")
        os.environ["FAKE_TAMPER"] = str(env.kit / "phaseA" / "answer-key.json")
        try:
            code, data, _ = env.case("A")
            self.assertEqual(code, bi.EXIT_GUARD)
            self.assertEqual(data["outcome"], "stop:guard_violation")
        finally:
            del os.environ["FAKE_TAMPER"]
            env.close()

    def test_quota_stop(self):
        env = Env(worker="worker-quota")
        try:
            code, data, _ = env.case("A")
            self.assertEqual(code, bi.EXIT_QUOTA)
            self.assertTrue(data["outcome"].startswith("stop:quota"))
        finally:
            env.close()

    def test_environment_block_stops_before_checker(self):
        env = Env(worker="worker-blocked")
        try:
            code, data, out = env.case("A")
            self.assertEqual(code, bi.EXIT_CONFIG)
            self.assertEqual(data["outcome"], "stop:not_an_md_problem:environment")
            self.assertFalse((out / "checker").exists())
        finally:
            env.close()

    def test_outside_paths_ignores_shell_launcher_and_urls(self):
        wd = Path("E:/T/run1/work")
        cmds = ['"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command "Get-Content -Raw .\\notes.md"',
                "/bin/bash -lc 'cat ./notes.md'",
                'pwsh.exe -NoProfile -Command "curl https://api.example/v2/x"']
        self.assertEqual(bi.outside_paths(cmds, wd), [])
        bad = ['"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command "Get-Content C:\\Users\\x\\secret.md"',
               "/bin/bash -lc 'cat /home/x/notes.md'"]
        self.assertEqual(len(bi.outside_paths(bad, wd)), 2)
        self.assertEqual(bi.outside_paths(['pwsh -Command "type E:\\T\\run1\\work\\a.md"'], wd), [])

    def test_reads_with_doubled_backslashes(self):
        cmd = '"C:\\\\Program Files\\\\pwsh.exe" -Command "Get-Content -Raw .\\\\notes\\\\a.md"'
        self.assertEqual(bi.file_reads([cmd], ["notes/a.md", "b.md"], Path("E:/T/w")), ["notes/a.md"])
        self.assertEqual(bi.outside_paths([cmd], Path("E:/T/w")), [])

    def test_token_cap_stops_before_running(self):
        env = Env(cap=1000)
        try:
            code, data, out = env.case("A")
            self.assertEqual(code, bi.EXIT_QUOTA)
            self.assertFalse((out / "baseline" / "run1").exists())
        finally:
            env.close()


class PartsTests(unittest.TestCase):
    def test_decide_flaky_is_not_md(self):
        base = {"bar_met": False, "confirmed": [], "flaky": ["A1"], "score": 5}
        self.assertEqual(bi.decide([base]), "stop:not_an_md_problem:flaky")
        base = {"bar_met": False, "confirmed": ["A1"], "score": 5}
        self.assertEqual(bi.decide([base]), "continue")
        self.assertEqual(bi.decide([base, {"bar_met": False, "score": 6}, {"bar_met": False, "score": 7},
                                    {"bar_met": False, "score": 8}]), "stop:max_rounds")

    def test_leak_scan_matches_both_slashes(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "tools").mkdir()
            (tmp / "tools" / "a.md").write_text("Path: C:/Work/Sample\nharbor-apps is fine\n", encoding="utf-8")
            hits = bi.scan_leaks(tmp, None, ["C:\\Work\\Sample", "harbor-app"], [])
            self.assertEqual([(h["line"], h["term"]) for h in hits], [(1, "C:\\Work\\Sample")])
        finally:
            shutil.rmtree(tmp)

    def test_diff_and_blocks(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            a, b = tmp / "a.md", tmp / "b.md"
            a.write_text("\n".join(f"line {i}" for i in range(30)), encoding="utf-8")
            b.write_text("\n".join(("changed" if i == 5 else f"line {i}") for i in range(30)), encoding="utf-8")
            d = bi.write_diff(a, b, tmp / "d.html")
            self.assertEqual(d["blocks"], 1)
            self.assertIn("<table", (tmp / "d.html").read_text(encoding="utf-8"))
            b.write_text("\n".join(("changed" if i in (2, 20) else f"line {i}") for i in range(30)), encoding="utf-8")
            self.assertEqual(bi.write_diff(a, b, tmp / "d.html")["blocks"], 2)
        finally:
            shutil.rmtree(tmp)

    def test_reads_from_windows_and_posix_commands(self):
        files = ["bSmart/Library/index.md", "bSmart/Library/tools/index.md", "sources/x.md"]
        cmds = ["powershell -Command Get-Content 'E:\\T\\run1\\work\\bSmart\\Library\\tools\\index.md'",
                "bash -lc 'cat ./bSmart/Library/index.md sources/x.md'"]
        self.assertEqual(bi.file_reads(cmds, files, Path("E:\\T\\run1\\work")),
                         ["bSmart/Library/tools/index.md", "bSmart/Library/index.md", "sources/x.md"])

    def test_card_and_pr_text(self):
        env = Env()
        try:
            s = bi.load_settings(env.instance)
            kit = bi.load_kit(env.kit)
            card = bi.render_card({"what": "did not save facts", "md": kit["target_md"], "phase": "A"},
                                  bi.estimate(kit, "A", s), s)
            self.assertIn("tokens", card)
            self.assertNotIn("{", card)
            case = {"best": "c1", "history": [{"score": 9, "max_score": 27},
                                              {"label": "c1", "score": 27, "max_score": 27,
                                               "reason": "clarify saving for harbor-app"}],
                    "final_diff": {"word_delta": 12}}
            text, hits = bi.pr_text(case, kit["target_md"], ["harbor-app"], [])
            self.assertEqual(hits, ["harbor-app"])
        finally:
            env.close()


class DocsTests(unittest.TestCase):
    def test_critic_md_cause(self):
        self.assertIn("MD cause", (ROOT / "bSmart-Extensions/bCritic/critic.md").read_text(encoding="utf-8"))
        self.assertIn("MD cause", (ROOT / "bSmart-Extensions/bCritic/templates/critique.template.md").read_text(encoding="utf-8"))

    def test_guardrails_documented(self):
        text = " ".join((EXT / "improve.md").read_text(encoding="utf-8").split())
        for phrase in ("never edits the checker, the answer key", "One change per candidate",
                       "stop after 2 rounds in a row with no higher score", "not_an_md_problem",
                       "one pull request per approved change", "explicit OK"):
            self.assertIn(phrase, text)

    def test_registered(self):
        for rel in ("bSmart.md", "bSmart_Features.md", "bSmart_Docs/extensions.md", "README.md",
                    "bSmart-Extensions/README.md", "bSmart_Version.md"):
            self.assertIn("bImprove", (ROOT / rel).read_text(encoding="utf-8"), rel)


if __name__ == "__main__":
    unittest.main()
