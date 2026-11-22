"""Design context (0.1.57): ADR consult, project glossary, change risk.

Covers the report-only glossary check in bKnowledgeCheck, the bADR installer,
and the wording the roles rely on.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "bSmart-Extensions"
SCRIPT = ROOT / "scripts" / "bKnowledgeCheck"
INSTALLER = EXT / "bADR" / "scripts" / "install-badr.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bk = load("bsmart_knowledge_design_context", ROOT / "scripts" / "bsmart_knowledge.py")
badr = load("install_badr_under_test", INSTALLER)


def write(path: Path, text: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class GlossaryBase(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="bsmart-glossary-"))
        self.addCleanup(shutil.rmtree, self.temp, True)
        self.content = self.temp / "bSmart"
        (self.content / "Library").mkdir(parents=True)
        self.projects = self.temp / "projects"
        self.glossary = self.projects / "shop" / "glossary"
        self.glossary.mkdir(parents=True)

    def kinds(self, folder: Path | None = None) -> set[tuple[str, str]]:
        report = bk.check_glossary(folder or self.glossary, "test")
        return {(f.kind, f.rel) for f in report.findings}

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        env.pop("BSMART_KNOWLEDGE_CHECK", None)
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--content-root", str(self.content),
             "--projects-root", str(self.projects), *args],
            text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, check=False,
        )


class GlossaryCheckTests(GlossaryBase):
    def clean(self):
        write(self.glossary / "index.md",
              "# Glossary index\n\n- **Order** - A request to buy items. _Avoid:_ purchase. -> [O.md](O.md#order)\n")
        write(self.glossary / "O.md", "# O\n\n## Order\n\nA request to buy items.\n")

    def test_clean_glossary_passes(self):
        self.clean()
        self.assertEqual(self.kinds(), set())

    def test_missing_index_and_stray_files(self):
        write(self.glossary / "O.md", "# O\n\n## Order\n\nA request.\n")
        write(self.glossary / "notes.md")
        (self.glossary / "module").mkdir()
        found = self.kinds()
        self.assertIn(("glossary_missing_index", "."), found)
        self.assertIn(("glossary_stray_file", "notes.md"), found)
        self.assertIn(("glossary_stray_file", "module/"), found)

    def test_unindexed_empty_and_broken_link(self):
        self.clean()
        write(self.glossary / "P.md", "# P\n")
        write(self.glossary / "index.md",
              (self.glossary / "index.md").read_text(encoding="utf-8")
              + "- **Quote** - An offer with a price. -> [Q.md](Q.md#quote)\n")
        found = self.kinds()
        self.assertIn(("glossary_unindexed", "P.md"), found)
        self.assertIn(("glossary_empty_file", "P.md"), found)
        self.assertIn(("glossary_broken_link", "Q.md"), found)

    def test_long_line_is_advisory(self):
        long = " ".join(["word"] * 30)
        write(self.glossary / "index.md", f"- **Order** - {long}. _Avoid:_ purchase, a, b, c, d, e, f.\n")
        report = bk.check_glossary(self.glossary, "test")
        self.assertEqual([f.kind for f in report.findings], ["glossary_long_line"])
        self.assertEqual(report.problems, [])
        write(self.glossary / "index.md", "- **Order** - A request to buy items. _Avoid:_ " + long + "\n")
        self.assertEqual(self.kinds(), set())  # _Avoid:_ and the pointer do not count

    def test_parent_conflict_one_hop_and_label(self):
        self.clean()
        parent = self.projects / "core" / "glossary"
        write(parent / "index.md", "- **order** - The parent meaning.\n- **Item** - A thing for sale.\n")
        sibling = self.projects / "other" / "glossary"
        write(sibling / "index.md", "- **Order** - A sibling meaning.\n")
        write(self.glossary / "RELATED.md",
              "# Related glossaries\n\n- [../../core/glossary/](../../core/glossary/index.md) - core product: parent\n"
              "- [../../other/glossary/](../../other/glossary/) - other product: shared data model\n")
        report = bk.check_glossary(self.glossary, "test")
        conflicts = [(f.kind, f.detail) for f in report.findings]
        self.assertEqual(conflicts, [("glossary_conflict", "Order")])  # siblings are not compared

    def test_related_broken_link(self):
        self.clean()
        write(self.glossary / "RELATED.md", "- [../../gone/glossary/](../../gone/glossary/) - gone: parent\n")
        self.assertIn(("glossary_broken_link", "../../gone/glossary"), self.kinds())

    def test_commented_template_examples_are_not_links(self):
        index = (ROOT / "bSmart_Templates" / "glossary-index.template.md").read_text(encoding="utf-8")
        write(self.glossary / "index.md", index)
        write(self.glossary / "RELATED.md",
              (ROOT / "bSmart_Templates" / "glossary-related.template.md").read_text(encoding="utf-8"))
        self.assertEqual(self.kinds(), set())
        self.assertEqual(bk.glossary_terms(self.glossary / "index.md"), [])

    def test_lowercase_letter_files_are_accepted(self):
        write(self.glossary / "index.md", "- **Order** - A request. -> [o.md](o.md)\n")
        write(self.glossary / "o.md", "# o\n\n## Order\n\nA request.\n")
        write(self.glossary / "0.md", "# 0\n\n## 3D view\n\nA view.\n")
        write(self.glossary / "index.md", "- **Order** - A request. -> [o.md](o.md)\n- **3D view** - A view. -> [0.md](0.md)\n")
        self.assertEqual(self.kinds(), set())

    def test_discovery_uses_glossary_path(self):
        write(self.projects / "shop" / "project.md", "```yaml\nproject:\n  name: shop\n```\n")
        self.assertEqual([p for _, p in bk.glossary_roots(self.projects)], [self.glossary])
        custom = self.projects / "plant" / "docs" / "terms"
        custom.mkdir(parents=True)
        write(self.projects / "plant" / "project.md", "project:\n  glossary_path: docs/terms/  # custom\n")
        write(self.projects / "bad" / "project.md", "  glossary_path: ../escape\n")
        (self.projects / "bad" / "glossary").mkdir(parents=True)
        roots = dict(bk.glossary_roots(self.projects))
        self.assertEqual(roots["glossary plant"], custom)
        self.assertEqual(roots["glossary bad"], self.projects / "bad" / "glossary")
        self.assertEqual(list(dict(bk.glossary_roots(self.projects, "plant")).values()), [custom])

    def test_no_glossary_folder_means_nothing(self):
        shutil.rmtree(self.glossary)
        self.assertEqual(bk.glossary_roots(self.projects), [])

    def test_cli_reports_and_fix_never_writes_glossary(self):
        write(self.glossary / "O.md", "# O\n")
        before = sorted(p.name for p in self.glossary.iterdir())
        result = self.run_cli("--fix")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("glossary_missing_index", result.stdout)
        self.assertIn("1 glossary folder(s)", result.stdout)
        self.assertEqual(sorted(p.name for p in self.glossary.iterdir()), before)
        payload = json.loads(self.run_cli("--json").stdout)
        labels = {r["label"] for r in payload}
        self.assertIn("glossary shop", labels)

    def test_startup_summary_counts_glossary_findings(self):
        bk.write_state(self.content, "done", [])
        write(self.content / "Library" / "index.md", "# Library\n")
        self.assertEqual(self.run_cli("--summary").stdout.strip(), "")
        write(self.glossary / "stray.md")
        line = self.run_cli("--summary").stdout
        self.assertIn("Knowledge: 2 layout finding(s)", line)  # stray file + missing index


class ModuleGlossaryTests(GlossaryBase):
    def labels(self, project: str | None = None, budget=None) -> dict[str, Path]:
        return dict(bk.glossary_roots(self.projects, project, budget))

    def test_finds_module_glossaries_under_the_project_and_skips_noise(self):
        shop = self.projects / "shop"
        module = shop / "repo" / "src" / "billing" / "glossary"
        write(module / "index.md", "- **Invoice** - A bill.\n")
        for skipped in ("node_modules/pkg", "vendor/lib", ".git/x", "knowledge/tools", "build", "data/raw"):
            write(shop / skipped / "glossary" / "index.md", "- **Noise** - Not a glossary.\n")
        deep = shop / "a" / "b" / "c" / "d" / "e" / "f" / "g" / "glossary"
        write(deep / "index.md", "- **Deep** - Too deep.\n")
        labels = self.labels()
        self.assertEqual(labels, {"glossary shop": self.glossary, "glossary shop:repo/src/billing": module})

    def test_module_repos_outside_the_project(self):
        repo = self.temp / "code" / "app"
        module = repo / "modules" / "pay" / "glossary"
        write(module / "index.md", "- **Payment** - Money received.\n")
        other = self.temp / "code" / "tool"
        write(other / "glossary" / "index.md", "- **Tool** - A tool.\n")
        write(self.projects / "shop" / "project.md",
              f"project:\n  module_repos: ['{repo.as_posix()}', ../../code/tool]  # repos\n")
        found = set(self.labels().values())
        self.assertEqual(found, {self.glossary, module, other / "glossary"})
        write(self.projects / "shop" / "project.md",
              f"project:\n  module_repos:\n    - {repo.as_posix()}\n    - {repo.as_posix()}\n  other: x\n")
        self.assertEqual(set(self.labels("shop").values()), {self.glossary, module})  # no duplicates

    def test_placeholder_and_missing_repos_are_ignored(self):
        write(self.projects / "shop" / "project.md", "  module_repos: [<path>, missing/repo]\n")
        self.assertEqual(list(self.labels().values()), [self.glossary])

    def test_module_term_conflicts_with_parent(self):
        write(self.glossary / "index.md", "- **Invoice** - The shared bill.\n")
        module = self.projects / "shop" / "repo" / "billing" / "glossary"
        write(module / "index.md", "- **Invoice** - A module bill.\n- **Dunning** - Reminder flow.\n")
        write(module / "RELATED.md", "- [parent](../../../glossary/index.md) - shop core: parent\n"
                                     "- [AI coding vocabulary](https://www.aicodingdictionary.com/) - external\n")
        report = bk.check_glossary(module, "test")
        self.assertEqual([(f.kind, f.detail) for f in report.findings], [("glossary_conflict", "Invoice")])
        result = self.run_cli("--project", "shop")
        self.assertIn("[glossary shop:repo/billing]", result.stdout)
        self.assertIn("glossary_conflict", result.stdout)

    def test_exhausted_budget_stops_discovery_quietly(self):
        write(self.projects / "shop" / "repo" / "glossary" / "index.md", "- **X** - Y.\n")
        budget = bk.Budget(entries=0)
        budget.spend()
        self.assertEqual(self.labels(budget=budget), {"glossary shop": self.glossary})  # no module walk
        bk.write_state(self.content, "done", [])
        result = self.run_cli("--summary", "--max-seconds", "0.000001")
        self.assertEqual(result.returncode, 0, result.stderr)


class CodingStandardsTests(GlossaryBase):
    def test_missing_listed_standards_file_is_reported(self):
        shop = self.projects / "shop"
        write(shop / "docs" / "style.md", "# Style\n")
        write(shop / "project.md", "project:\n  coding_standards: [docs/style.md, docs/gone.md]\n")
        reports = bk.check_standards(self.projects)
        self.assertEqual([(r.label, [(f.kind, f.rel) for f in r.findings]) for r in reports],
                         [("standards shop", [("standards_missing_file", "docs/gone.md")])])
        result = self.run_cli("--project", "shop")
        self.assertEqual(result.returncode, 1)
        self.assertIn("standards_missing_file: docs/gone.md", result.stdout)
        self.assertTrue((shop / "docs" / "style.md").is_file())  # never written

    def test_block_list_and_no_field(self):
        shop = self.projects / "shop"
        write(shop / "lint.md")
        write(shop / "project.md", "project:\n  coding_standards:\n    - lint.md\n  other: x\n")
        self.assertEqual(bk.check_standards(self.projects), [])
        write(shop / "project.md", "project:\n  name: shop\n")
        self.assertEqual(bk.check_standards(self.projects), [])
        self.assertEqual(bk.project_list(shop, "coding_standards"), [])

    def test_startup_counts_missing_standards_file(self):
        bk.write_state(self.content, "done", [])
        write(self.content / "Library" / "index.md", "# Library\n")
        write(self.projects / "shop" / "project.md", "  coding_standards: [nope.md]\n")
        self.assertIn("Knowledge: 1 layout finding(s)", self.run_cli("--summary").stdout)

    def test_convention_docs(self):
        context = flat(ROOT / "bSmart_Protocols" / "design-context.md")
        for term in ["## 5. Coding standards and the two-axis review", "`CODING_STANDARDS.md`",
                     "two axes, always", "Spec axis", "Standards axis", "`coding_standards`",
                     "Never pass the whole file", "Prefer determinism", "report-only",
                     "skip the standards axis with no note, never fail", "`## Summary`"]:
            self.assertIn(term, context)
        template = (ROOT / "bSmart_Templates" / "coding-standards.template.md").read_text(encoding="utf-8")
        self.assertIn("## Summary", template)
        self.assertIn("standards_rules:", flat(EXT / "bArchitect" / "architect.md"))
        critic = flat(EXT / "bCritic" / "critic.md")
        self.assertIn("two axes, always", critic)
        self.assertIn("Axes (code reviews)", flat(EXT / "bCritic" / "templates" / "critique.template.md"))
        self.assertIn("## Review axes", flat(EXT / "bSwarm" / "templates" / "jobs" / "report.template.md"))
        self.assertIn("two axes: spec and coding standards", flat(EXT / "bSwarm" / "bswarm-protocol.md"))
        self.assertIn("coding_standards:", flat(ROOT / "bSmart_Protocols" / "projects.md"))
        self.assertIn("coding_standards:", flat(ROOT / "bSmart_Templates" / "project.template.md"))


class BlackBoxTestDocsTests(unittest.TestCase):
    def test_protocol_section(self):
        context = flat(ROOT / "bSmart_Protocols" / "design-context.md")
        for term in ["## 6. Black-box tests and test economy", "public interface",
                     "a public contract or behaviour", "a real bug or regression", "a risky edge case",
                     "pins internals", "trivial getter", "tautological", "duplicates another test",
                     "about 3-6 new tests per ticket", "one-line reason", "**Suite prune:**",
                     "deep module puts much behaviour behind a small interface", "deletion test",
                     "never delete a test, never change code, never apply a proposal, and never open a pull request"]:
            self.assertIn(term, context)

    def test_roles_bswarm_and_templates(self):
        architect = flat(EXT / "bArchitect" / "architect.md")
        for term in ["test_plan:", "interfaces:", "budget:"]:
            self.assertIn(term, architect)
        coder = flat(EXT / "bCoder" / "coder.md")
        self.assertIn("through the public interface only", coder)
        self.assertIn("one regression test", coder)
        critic = flat(EXT / "bCritic" / "critic.md")
        self.assertIn("pin internals or are brittle, tautological, or redundant", critic)
        swarm = flat(EXT / "bSwarm" / "bswarm-protocol.md")
        self.assertIn("never deletes tests, applies a proposal, or opens a pull request", swarm)
        self.assertIn("## Test plan", flat(EXT / "bSwarm" / "templates" / "jobs" / "plan.template.md"))
        report = flat(EXT / "bSwarm" / "templates" / "jobs" / "report.template.md")
        self.assertIn("## Tests", report)
        self.assertIn("proposals only; nothing applied", report)
        self.assertIn("test plan on each ticket", flat(ROOT / "bSmart.md"))

    def test_rules_stay_language_agnostic(self):
        section = (ROOT / "bSmart_Protocols" / "design-context.md").read_text(encoding="utf-8")
        section = section.split("## 6. Black-box tests", 1)[1].split("### Only if there's an issue", 1)[0].lower()
        for word in ("jest", "pytest", "typescript", "matlab", "junit", "mock"):
            self.assertNotIn(word, section)


class AdrInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="bsmart-badr-"))
        self.addCleanup(shutil.rmtree, self.temp, True)

    def test_installs_short_template_and_index(self):
        created = badr.install(self.temp)
        names = sorted(p.name for p in created)
        self.assertEqual(names, ["README.md", "template-short.md", "template.md"])
        index = (self.temp / "docs" / "adr" / "README.md").read_text(encoding="utf-8")
        self.assertIn("Hard to reverse", index)
        self.assertIn("template-short.md", index)
        self.assertEqual(badr.install(self.temp), [])  # create-only

    def test_custom_adr_path_and_guard(self):
        result = subprocess.run([sys.executable, str(INSTALLER), str(self.temp), "--adr-path", "knowledge/adr"],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.temp / "knowledge" / "adr" / "template-short.md").is_file())
        bad = subprocess.run([sys.executable, str(INSTALLER), str(self.temp), "--adr-path", "../out"],
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(bad.returncode, 2)
        self.assertFalse((self.temp.parent / "out").exists())

    def test_adr_folder_inside_knowledge_passes_the_layout_check(self):
        knowledge = self.temp / "knowledge"
        write(knowledge / "index.md", "- [adr/](adr/README.md) - decision records\n")
        badr.install(self.temp, adr_path="knowledge/adr")
        found = {f.kind for f in bk.check_root(knowledge, "test").findings}
        self.assertEqual(found, set())


class DesignContextDocsTests(unittest.TestCase):
    def test_protocol_is_the_one_home(self):
        text = flat(ROOT / "bSmart_Protocols" / "design-context.md")
        for term in ["## 1. Strategic note", "2-3 lines", "## 2. ADR consult", "keyword sketch",
                     "Read only the ADRs that match", "never fail", "Hard to reverse",
                     "Surprising without context", "A real trade-off", "template-short.md",
                     "## 3. Project glossary", "never inside it", "One hop only", "`RELATED.md`",
                     "the parent wins", "Admission bar", "only the architect, or bAsk",
                     "naming drift", "`knowledge_upkeep`", "## 4. Change risk", "two-way | one-way",
                     "small | medium | large", "may only raise", "confirms or raises",
                     "No new approval gate", "instance's audit model", "`not launched`",
                     "Heads-up", "### Only if there's an issue"]:
            self.assertIn(term, text)
        index = flat(ROOT / "bSmart_Protocols" / "protocols.md")
        self.assertIn("`design-context.md`", index)
        self.assertIn("design-context.md", flat(ROOT / "bSmart_Map.md"))

    def test_core_habit_and_upkeep(self):
        core = flat(ROOT / "bSmart.md")
        self.assertIn("design_context:", core)
        self.assertIn("details: bSmart_Protocols/design-context.md", core)
        self.assertIn("also search its index.md for the touched names", core)
        self.assertIn("**Design context.**", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_roles_point_to_the_protocol(self):
        architect = flat(EXT / "bArchitect" / "architect.md")
        for term in ["strategic_note:", "change_risk:", "adrs_consulted:", "glossary_terms:", "keyword sketch"]:
            self.assertIn(term, architect)
        coder = flat(EXT / "bCoder" / "coder.md")
        self.assertIn("do not open ADRs, the glossary, or the coding standards", coder)
        self.assertIn("`standards_rules`", coder)
        self.assertIn("never lower it", coder)
        critic = flat(EXT / "bCritic" / "critic.md")
        self.assertIn("search the ADR index yourself", critic)
        self.assertIn("A downgrade needs a one-line reason", critic)
        ask = flat(EXT / "bAsk" / "interview.md")
        self.assertIn("write the index line and the letter entry in the same step", ask)
        self.assertIn("all three gates", ask)
        swarm = flat(EXT / "bSwarm" / "bswarm-protocol.md")
        self.assertIn("### Design context and change risk", swarm)
        self.assertIn("this is not a preflight block", swarm)
        for path in (EXT / "bArchitect" / "architect.md", EXT / "bCoder" / "coder.md",
                     EXT / "bCritic" / "critic.md", EXT / "bAsk" / "interview.md",
                     EXT / "bSwarm" / "bswarm-protocol.md"):
            self.assertIn("design-context.md", flat(path), path.name)

    def test_templates(self):
        templates = ROOT / "bSmart_Templates"
        for name in ("glossary-index.template.md", "glossary-letter.template.md", "glossary-related.template.md"):
            self.assertTrue((templates / name).is_file(), name)
            self.assertIn(f"bSmart_Templates/{name}", flat(ROOT / "bSmart_Protocols" / "projects.md"))
        report = flat(EXT / "bSwarm" / "templates" / "jobs" / "report.template.md")
        self.assertIn("## Change risk", report)
        self.assertIn("## Strategic note", flat(EXT / "bSwarm" / "templates" / "jobs" / "plan.template.md"))
        self.assertTrue((EXT / "bADR" / "templates" / "template-short.md").is_file())
        related = (templates / "glossary-related.template.md").read_text(encoding="utf-8")
        self.assertIn("https://www.aicodingdictionary.com/", related)
        context = flat(ROOT / "bSmart_Protocols" / "design-context.md")
        for term in ["https://www.aicodingdictionary.com/", "never load it by default", "**Module glossaries.**",
                     "**Discovery.**", "`module_repos`", "label `parent`", "only in task reports, not at startup"]:
            self.assertIn(term, context)
        self.assertIn("module_repos:", flat(ROOT / "bSmart_Protocols" / "projects.md"))
        project = flat(templates / "project.template.md")
        for field in ("adr_path:", "glossary_path:", "module_repos:", "one_way_examples:"):
            self.assertIn(field, project)

    def test_no_hardcoded_model_in_shared_rules(self):
        for path in (ROOT / "bSmart_Protocols" / "design-context.md", EXT / "bSwarm" / "bswarm-protocol.md"):
            text = flat(path).lower()
            for model in ("opus", "sonnet", "gpt-", "gemini"):
                self.assertNotIn(model, text, path.name)

    def test_version_and_news(self):
        text = (ROOT / "bSmart_Version.md").read_text(encoding="utf-8")
        current = re.search(r"current_version: 0\.1\.(\d+)", text)
        self.assertIsNotNone(current)
        self.assertGreaterEqual(int(current.group(1)), 57)
        section = text.split("## 0.1.57-draft", 1)[1].split("\n## ", 1)[0]
        news = section.split("news: |", 1)[1].split("scope:", 1)[0]
        self.assertTrue(news.isascii())


if __name__ == "__main__":
    unittest.main()
