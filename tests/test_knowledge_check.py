"""bKnowledgeCheck: layout check, safe fixes, startup summary, one-time migration."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bKnowledgeCheck"
START = ROOT / "bStart.py"


def load_module():
    path = ROOT / "scripts" / "bsmart_knowledge.py"
    spec = importlib.util.spec_from_file_location("bsmart_knowledge_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


bk = load_module()


def write(path: Path, text: str = "note\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def flat(path: Path) -> str:
    return " ".join(read(path).split())


class KnowledgeBase(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="bsmart-knowledge-"))
        self.addCleanup(shutil.rmtree, self.temp, True)
        self.content = self.temp / "bSmart"
        self.library = self.content / "Library"
        self.projects = self.temp / "projects"
        self.library.mkdir(parents=True)
        self.projects.mkdir()

    def kinds(self, root: Path) -> set[tuple[str, str]]:
        return {(f.kind, f.rel) for f in bk.check_root(root, "test").findings}

    def run_cli(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        full_env = dict(os.environ, PYTHONIOENCODING="utf-8")
        full_env.pop("BSMART_KNOWLEDGE_CHECK", None)
        if env:
            full_env.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--content-root", str(self.content),
             "--projects-root", str(self.projects), *args],
            text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=full_env, check=False,
        )


class CheckTests(KnowledgeBase):
    def test_clean_tree_passes(self):
        write(self.library / "index.md", "- [tools/](tools/index.md) - apps\n")
        write(self.library / "tools" / "index.md", "- [some-app/](some-app/index.md) - an app\n")
        write(self.library / "tools" / "some-app" / "index.md", "- [setup](setup.md) - how to set it up\n")
        write(self.library / "tools" / "some-app" / "setup.md")
        self.assertEqual(self.kinds(self.library), set())
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 finding(s)", result.stdout)

    def test_root_files_and_allowlist(self):
        for name in ("README.md", "index.md", "CHANGELOG.md", "CATEGORIES.md", "task-context-routing.md"):
            write(self.library / name, "# x\n")
        write(self.library / "loose-note.md")
        write(self.library / "hidden" / ".keep")
        write(self.library / ".gitkeep")
        self.assertEqual(self.kinds(self.library), {("root_file", "loose-note.md")})

    def test_notes_directly_in_tools_or_general_but_not_code(self):
        write(self.library / "index.md", "- [code/](code/index.md)\n- [tools/](tools/index.md)\n- [general/](general/index.md)\n")
        write(self.library / "code" / "index.md", "- [style](style.md) - x\n")
        write(self.library / "code" / "style.md")
        write(self.library / "tools" / "index.md", "- [app](app.md) - x\n")
        write(self.library / "tools" / "app.md")
        write(self.library / "general" / "index.md", "- [misc/](misc/index.md) - x\n- [g](g.md) - x\n")
        write(self.library / "general" / "g.md")
        write(self.library / "general" / "misc" / "index.md", "- [n](n.md) - x\n")
        write(self.library / "general" / "misc" / "n.md")
        kinds = self.kinds(self.library)
        self.assertIn(("default_root_file", "tools/app.md"), kinds)
        self.assertIn(("default_root_file", "general/g.md"), kinds)
        self.assertIn(("general_note", "general/misc/n.md"), kinds)
        self.assertNotIn(("general_note", "general/g.md"), kinds)
        self.assertFalse(any(path.startswith("code/") for _, path in kinds))

    def test_general_note_is_advisory_only(self):
        write(self.library / "index.md", "- [general/](general/index.md)\n")
        write(self.library / "general" / "index.md", "- [misc/](misc/index.md) - x\n")
        write(self.library / "general" / "misc" / "index.md", "- [n](n.md) - x\n")
        write(self.library / "general" / "misc" / "n.md")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("advisory general_note: general/misc/n.md", result.stdout)

    def test_missing_index_unindexed_and_nested_topics(self):
        write(self.library / "index.md", "- [code/](code/index.md)\n")
        write(self.library / "code" / "index.md", "nothing listed\n")
        write(self.library / "code" / "matlab" / "deep" / "deeper" / "n.md")
        write(self.library / "some-domain" / "a.md")
        kinds = self.kinds(self.library)
        self.assertIn(("unindexed", "code/matlab/"), kinds)
        self.assertIn(("missing_index", "code/matlab/"), kinds)
        self.assertIn(("missing_index", "code/matlab/deep/deeper/"), kinds)
        self.assertIn(("missing_index", "some-domain/"), kinds)
        self.assertIn(("unindexed", "some-domain/"), kinds)

    def test_readme_counts_as_index_and_catalogue(self):
        write(self.library / "README.md", "# Library\n\n- some-domain/ - a subject area\n- [other-domain/](other-domain/README.md)\n")
        write(self.library / "some-domain" / "README.md", "# Some domain\n- [a](a.md)\n- `b.md`\n")
        write(self.library / "some-domain" / "a.md")
        write(self.library / "some-domain" / "b.md")
        write(self.library / "other-domain" / "README.md", "- [c](c.md)\n")
        write(self.library / "other-domain" / "c.md")
        self.assertEqual(self.kinds(self.library), set())

    def test_attachment_folder_needs_no_index(self):
        write(self.library / "index.md", "- [tools/](tools/index.md)\n")
        write(self.library / "tools" / "index.md", "- [app/](app/index.md)\n")
        write(self.library / "tools" / "app" / "index.md", "- [n](n.md) - x\n")
        write(self.library / "tools" / "app" / "n.md")
        write(self.library / "tools" / "app" / "images" / "shot.png", "png")
        self.assertEqual(self.kinds(self.library), set())

    def test_broken_link_and_placeholder(self):
        write(self.library / "index.md", "- [tools/](tools/index.md)\n- [web](https://example.com)\n")
        write(self.library / "tools" / "index.md", f"- [gone](gone.md) - x\n- [a](a.md) - {bk.PLACEHOLDER}\n")
        write(self.library / "tools" / "a.md")
        kinds = self.kinds(self.library)
        self.assertIn(("broken_link", "tools/gone.md"), kinds)
        self.assertIn(("placeholder", "tools/index.md"), kinds)

    def test_nested_knowledge_root_is_reported(self):
        write(self.library / "knowledge" / "tools" / "app" / "index.md", "- x\n")
        self.assertIn(("nested_root", "knowledge/"), self.kinds(self.library))

    def test_json_and_exit_code(self):
        write(self.library / "loose.md")
        result = self.run_cli("--json")
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertEqual(data[0]["label"], "library")
        self.assertEqual(data[0]["findings"][0]["kind"], "root_file")

    def test_project_roots_are_found(self):
        write(self.projects / "demo" / "knowledge" / "loose.md")
        write(self.projects / "other" / "project.md")
        result = self.run_cli("--project", "demo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("[project demo]", result.stdout)
        self.assertNotIn("[library]", result.stdout)
        self.assertIn("root_file: loose.md", result.stdout)


class FixTests(KnowledgeBase):
    def test_fix_creates_indexes_adds_entries_and_logs(self):
        write(self.library / "code" / "matlab" / "m.md")
        write(self.library / "code" / "style.md")
        write(self.library / "loose.md")
        changes = bk.fix_root(self.library, ROOT)
        self.assertTrue((self.library / "index.md").is_file())
        self.assertTrue((self.library / "code" / "index.md").is_file())
        self.assertTrue((self.library / "code" / "matlab" / "index.md").is_file())
        self.assertIn("[code/](code/index.md)", read(self.library / "index.md"))
        self.assertIn("[matlab/](matlab/index.md)", read(self.library / "code" / "index.md"))
        self.assertIn(f"[m](m.md) - {bk.PLACEHOLDER}", read(self.library / "code" / "matlab" / "index.md"))
        self.assertNotIn("loose", read(self.library / "index.md"))
        self.assertTrue((self.library / "loose.md").is_file(), "fix never moves notes")
        log = read(self.library / "CHANGELOG.md")
        self.assertIn("bKnowledgeCheck --fix: created code/matlab/index.md", log)
        self.assertEqual(len(changes), log.count("bKnowledgeCheck --fix:"))
        kinds = {k for k, _ in self.kinds(self.library)}
        self.assertEqual(kinds, {"root_file", "placeholder"})

    def test_fix_is_idempotent(self):
        write(self.library / "tools" / "app" / "n.md")
        bk.fix_root(self.library, ROOT)
        self.assertEqual(bk.fix_root(self.library, ROOT), [])

    def test_fix_keeps_readme_and_adds_index_pointing_to_it(self):
        readme = write(self.library / "topic" / "README.md", "# Topic\n- [a](a.md)\n")
        write(self.library / "topic" / "a.md")
        write(self.library / "topic" / "b.md")
        write(self.library / "README.md", "# Library\n- topic/ - things\n")
        bk.fix_root(self.library, ROOT)
        self.assertEqual(read(readme), "# Topic\n- [a](a.md)\n")
        index = read(self.library / "topic" / "index.md")
        self.assertIn("[README.md](README.md)", index)
        self.assertIn("[b](b.md)", index)
        self.assertNotIn("[a](a.md)", index)
        self.assertFalse((self.library / "index.md").exists(), "root README already lists the topic")

    def test_fix_removes_broken_links(self):
        write(self.library / "index.md", "- [tools/](tools/index.md) - apps\n")
        write(self.library / "tools" / "index.md", "# tools\n- [app/](app/index.md) - x\n- [gone](gone.md) - x\n")
        write(self.library / "tools" / "app" / "index.md", "- [n](n.md) - x\n")
        write(self.library / "tools" / "app" / "n.md")
        write(self.library / "README.md", "See [old](old/README.md) for history.\n")
        bk.fix_root(self.library, ROOT)
        self.assertNotIn("gone", read(self.library / "tools" / "index.md"))
        self.assertIn("[app/](app/index.md)", read(self.library / "tools" / "index.md"))
        self.assertEqual(read(self.library / "README.md"), "See old for history.\n")
        self.assertIn("removed broken link gone.md", read(self.library / "CHANGELOG.md"))
        self.assertEqual(self.kinds(self.library), set())

    def test_cli_fix_reports_changes(self):
        write(self.library / "tools" / "app" / "n.md")
        result = self.run_cli("--fix")
        self.assertIn("changed: created tools/app/index.md", result.stdout)
        self.assertEqual(result.returncode, 1)  # placeholders remain for the agent
        self.assertIn("placeholder", result.stdout)


class SummaryTests(KnowledgeBase):
    def test_summary_asks_for_migration_until_done(self):
        result = self.run_cli("--summary")
        self.assertEqual(result.returncode, 0)
        self.assertIn("one-time layout migration pending", result.stdout)
        self.assertIn("--migrate", result.stdout)

    def test_summary_is_silent_when_clean_and_counts_findings(self):
        bk.write_state(self.content, "done", [])
        result = self.run_cli("--summary")
        self.assertEqual(result.stdout, "")
        write(self.library / "loose.md")
        result = self.run_cli("--summary")
        self.assertIn("Knowledge: 1 layout finding(s)", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_summary_can_be_turned_off(self):
        result = self.run_cli("--summary", env={"BSMART_KNOWLEDGE_CHECK": "0"})
        self.assertEqual(result.stdout, "")

    def test_budget_marks_report_partial(self):
        for n in range(30):
            write(self.library / f"t{n}" / "n.md")
        budget = bk.Budget(entries=5)
        report = bk.check_root(self.library, "library", budget)
        self.assertTrue(report.partial)
        expired = bk.Budget(seconds=0.001)
        time.sleep(0.01)
        self.assertTrue(bk.check_root(self.library, "library", expired).partial)


class MigrationTests(KnowledgeBase):
    def make_instance(self):
        write(self.library / "README.md", "# Library\n- some-domain/ - a subject area\n")
        write(self.library / "CATEGORIES.md", "# Categories\n")
        write(self.library / "some-domain" / "README.md", "# Some domain\n- [a](a.md)\n")
        write(self.library / "some-domain" / "a.md")
        write(self.library / "old-loose-note.md", "loose\n")
        write(self.library / "knowledge" / "tools" / "index.md", "- [some-app/](some-app/index.md) - app\n")
        write(self.library / "knowledge" / "tools" / "some-app" / "index.md", "- [x](x.md) - x\n")
        write(self.library / "knowledge" / "tools" / "some-app" / "x.md")
        write(self.projects / "demo" / "knowledge" / "README.md", "# knowledge\n")
        write(self.projects / "demo" / "knowledge" / "code" / "calc.md")

    def test_migration_moves_up_builds_indexes_and_lists_loose_notes(self):
        self.make_instance()
        result = self.run_cli("--migrate")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertFalse((self.library / "knowledge").exists())
        self.assertTrue((self.library / "tools" / "some-app" / "x.md").is_file())
        for name in ("code", "tools", "general"):
            self.assertTrue((self.library / name / "index.md").is_file(), name)
            self.assertTrue((self.projects / "demo" / "knowledge" / name / "index.md").is_file(), name)
        self.assertEqual(read(self.library / "some-domain" / "README.md"), "# Some domain\n- [a](a.md)\n")
        self.assertIn("library: root_file: old-loose-note.md", result.stdout)
        self.assertTrue((self.library / "old-loose-note.md").is_file(), "migration never guesses a topic")
        log = read(self.library / "CHANGELOG.md")
        self.assertIn("knowledge migration: moved knowledge/tools to tools", log)
        state = bk.read_state(self.content)
        self.assertEqual(state["status"], "pending")
        self.assertFalse(bk.migration_done(self.content))

    def test_migration_finishes_once_after_the_agent_sorts(self):
        self.make_instance()
        self.run_cli("--migrate")
        target = self.library / "tools" / "hosts"
        target.mkdir(parents=True)
        (self.library / "old-loose-note.md").rename(target / "old-loose-note.md")
        result = self.run_cli("--migrate")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("knowledge migration: done", result.stdout)
        self.assertTrue(bk.migration_done(self.content))
        self.assertIn("[old-loose-note](old-loose-note.md)", read(target / "index.md"))
        again = self.run_cli("--migrate")
        self.assertIn("already done", again.stdout)
        forced = self.run_cli("--migrate", "--force")
        self.assertIn("knowledge migration: done", forced.stdout)

    def test_migration_never_overwrites_on_conflict(self):
        write(self.library / "tools" / "app" / "n.md", "root copy\n")
        write(self.library / "knowledge" / "tools" / "app" / "n.md", "nested copy\n")
        write(self.library / "knowledge" / "tools" / "app" / "same.md", "same\n")
        write(self.library / "tools" / "app" / "same.md", "same\n")
        result = self.run_cli("--migrate")
        self.assertEqual(read(self.library / "tools" / "app" / "n.md"), "root copy\n")
        self.assertEqual(read(self.library / "knowledge" / "tools" / "app" / "n.md"), "nested copy\n")
        self.assertFalse((self.library / "knowledge" / "tools" / "app" / "same.md").exists())
        self.assertIn("conflict, not moved: knowledge/tools/app/n.md", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_empty_instance_finishes_at_once(self):
        result = self.run_cli("--migrate")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(bk.migration_done(self.content))
        self.assertTrue((self.library / "general" / "index.md").is_file())

    def test_instance_upgrade_runs_the_migration_from_its_own_checkout(self):
        import runpy
        upgrade = runpy.run_path(str(ROOT / "scripts" / "bsmart-instance-upgrade"))
        workspace = self.temp
        system = workspace / "bSmart-System"
        system.mkdir()
        upgrade["migrate_knowledge"](workspace, system, self.projects)  # no script there: skipped
        self.assertFalse(bk.state_path(self.content).exists())
        (system / "scripts").symlink_to(ROOT / "scripts") if os.name != "nt" else shutil.copytree(ROOT / "scripts", system / "scripts")
        (system / "bSmart_Templates").mkdir()
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            upgrade["migrate_knowledge"](workspace, system, self.projects)
        self.assertTrue(bk.migration_done(self.content))


class StartupTests(KnowledgeBase):
    def run_start(self, env: dict | None = None) -> str:
        write(self.content / "bSmart_Agent.md", "# Agent\n\n```yaml\nagent:\n  name: T\n  operator: Test User\n```\n")
        full = dict(os.environ, BSMART_PROJECT_ROOT=str(self.projects))
        for key in ("BSMART_SESSION_PROJECT", "BSMART_SESSION_WORKSTREAM", "BSMART_KNOWLEDGE_CHECK"):
            full.pop(key, None)
        full.update(env or {})
        result = subprocess.run(
            [sys.executable, str(START), "--root", str(self.temp), "--skip-update", "--skip-integrity", "--no-record"],
            text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=full, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_startup_prints_one_knowledge_line_only_when_needed(self):
        output = self.run_start()
        self.assertIn("Knowledge: one-time layout migration pending", output)
        bk.write_state(self.content, "done", [])
        bk.fix_root(self.library, ROOT)
        self.assertNotIn("Knowledge:", self.run_start())
        write(self.library / "loose.md")
        self.assertIn("Knowledge: 1 layout finding(s)", self.run_start())
        self.assertNotIn("Knowledge:", self.run_start({"BSMART_KNOWLEDGE_CHECK": "off"}))


class DocsTests(unittest.TestCase):
    def test_protocol_covers_the_seven_habits_and_layout(self):
        text = flat(ROOT / "bSmart_Protocols" / "knowledge.md")
        for term in ["Look before guessing", "not found in knowledge", "Save on your own", "`Source:`", "`Date:`",
                     "Pick the place", "Topic folders only", "Index in the same step", "Corrections become knowledge",
                     "`glossary/`", "Keep it tidy", "`code/`, `tools/`, and `general/` are the defaults",
                     "last resort", "Topics nest to any depth", "`CATEGORIES.md`", "CHANGELOG.md",
                     "## One-time migration", "### Only if there's an issue", "knowledge-migration.yaml",
                     "## Code references and upkeep"]:
            self.assertIn(term, text)

    def test_one_layout_no_old_two_class_wording(self):
        old = ["Keep the two knowledge classes separate", "`knowledge/general/` holds file-independent",
               "knowledge/code/<stable-slug>.md", "category selection", "`library/` folder"]
        for path in [ROOT / "bSmart_Protocols" / "knowledge.md", ROOT / "bSmart_Protocols" / "projects.md",
                     ROOT / "bSmart_Features.md", *sorted((ROOT / "bSmart_Templates").glob("*.md"))]:
            text = flat(path)
            for phrase in old:
                self.assertNotIn(phrase, text, f"{path.name}: {phrase}")

    def test_core_manifest_map_features_readme(self):
        core = flat(ROOT / "bSmart.md")
        self.assertIn("knowledge_handling:", core)
        self.assertIn("python ./scripts/bKnowledgeCheck", core)
        self.assertIn("scripts/bKnowledgeCheck", flat(ROOT / "bSmart_Map.md"))
        self.assertIn("scripts/bKnowledgeCheck", flat(ROOT / "bSmart_Features.md"))
        self.assertIn("**Knowledge handling.**", read(ROOT / "README.md"))
        self.assertIn("Before writing a handoff, run `scripts/bKnowledgeCheck", flat(ROOT / "bSmart_Protocols" / "projects.md"))

    def test_templates_have_entries_marker(self):
        for name in ("knowledge-index.template.md", "knowledge-topic-index.template.md"):
            text = read(ROOT / "bSmart_Templates" / name)
            self.assertIn(bk.ENTRIES_MARKER, text)
        top = read(ROOT / "bSmart_Templates" / "knowledge-index.template.md")
        for name in bk.DEFAULT_TOPICS:
            self.assertIn(f"[{name}/]({name}/index.md)", top)

    def test_version_and_news(self):
        text = read(ROOT / "bSmart_Version.md")
        self.assertRegex(text, r"current_version: 0\.1\.(5[6-9]|[6-9]\d)")
        section = text.split("## 0.1.56-draft", 1)[1].split("\n## ", 1)[0]
        self.assertIn("news: |", section)
        news = section.split("news: |", 1)[1].split("scope:", 1)[0]
        self.assertTrue(news.isascii())


if __name__ == "__main__":
    unittest.main()
