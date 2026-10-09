from __future__ import annotations

import io
import json
import runpy
import contextlib
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "bsmart_session_projects.py"
UPGRADE = ROOT / "scripts" / "bsmart-instance-upgrade"

session = runpy.run_path(str(MODULE))
upgrade = runpy.run_path(str(UPGRADE))


class IndexTests(unittest.TestCase):
    def test_missing_index_is_generated_and_a_present_index_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "DigSoftware"
            project.mkdir()
            (project / "project.md").write_text("status: active\nobjective: unspecified\n", encoding="utf-8")
            rows, created = session["ensure_index"](root)
            self.assertTrue(created)
            self.assertEqual(rows[0]["name"], "DigSoftware")
            self.assertEqual(rows[0]["label"], "DS")
            self.assertEqual(session["short_label"]("DigSoftware"), "DS")
            index = root / "INDEX.md"
            index.write_text(index.read_text(encoding="utf-8").replace("| DS |", "| DSW |"), encoding="utf-8")
            (root / "Extra").mkdir()
            kept, created_again = session["ensure_index"](root)
            self.assertFalse(created_again)
            self.assertEqual(kept[0]["label"], "DSW")
            warnings = session["self_check"](root, kept)
            self.assertIn("Folder Extra is not in the index", warnings)
            added = session["repair_index"](root, kept)
            self.assertEqual(added, ["Extra"])
            repaired = session["read_index"](root)
            labels = {row["name"]: row["label"] for row in repaired if not row.get("invalid")}
            self.assertEqual(labels["DigSoftware"], "DSW")
            self.assertIn("Extra", labels)

    def test_node_and_python_agree_on_a_generated_row(self):
        text = "# bSmart project index\n#\nname | label | aliases | description | status\nDigSoftware | DS | dig; software | Reservoir software | active\n"
        rows = session["parse_index"](text)
        self.assertEqual(rows[0]["aliases"], ["dig", "software"])
        self.assertEqual(session["format_row"](rows[0]), "DigSoftware | DS | dig; software | Reservoir software | active")


class MigrationTests(unittest.TestCase):
    def test_backup_merges_handoff_asks_when_ambiguous_and_restores_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            content = workspace / "bSmart"
            roles = content / "Roles"
            roles.mkdir(parents=True)
            projects = workspace / "projects"
            alpha = projects / "Alpha"
            (alpha / "workstreams" / "Build").mkdir(parents=True)
            original_handoff = alpha / "handoff.md"
            original_handoff.write_text("# Handoff\n\nORIGINAL\n", encoding="utf-8")
            role = roles / "developer_role.md"
            role.write_text(
                "```yaml\nstate:\n  active_project: \"Alpha\"\n  active_workstream: \"none\"\n"
                "  current_focus: \"Ship the cut\"\n  task_handoff: \"Resume the parser\"\n"
                "  custom_note: \"keep me\"\n```\n",
                encoding="utf-8",
            )
            stream_role = roles / "review_role.md"
            stream_role.write_text(
                "active_project: Alpha\nactive_workstream: Build\ncurrent_focus: Review the log\n",
                encoding="utf-8",
            )
            missing = roles / "ghost_role.md"
            missing.write_text("active_project: Missing\ncurrent_focus: Nowhere\n", encoding="utf-8")
            legacy = content / "bSmart_State.md"
            legacy.write_text(
                "# State\n- Active project (short name): `Alpha`\n- Active workstream: `none`\n- Unknown: `retain`\n",
                encoding="utf-8",
            )
            (roles / "current_role.md").write_text("current_role: developer\n", encoding="utf-8")
            role_bytes = role.read_bytes()
            legacy_bytes = legacy.read_bytes()
            selector_bytes = (roles / "current_role.md").read_bytes()
            backup = workspace / ".bsmart-upgrade-backups" / "stamp"
            report = session["migrate_workspace"](workspace, backup, projects)
            text = "\n".join(report)
            self.assertIn("role_migration: backup", text)
            self.assertIn("migrated developer -> Alpha/handoff.md", text)
            self.assertIn("migrated review -> Alpha/workstreams/Build/handoff.md", text)
            self.assertIn("question:", text)
            self.assertIn("Missing", text)
            self.assertFalse((projects / "Missing").exists())
            handoff = original_handoff.read_text(encoding="utf-8")
            self.assertTrue(handoff.startswith("# Handoff\n\nORIGINAL"))
            self.assertIn("Ship the cut", handoff)
            self.assertIn("Resume the parser", handoff)
            self.assertIn("custom_note: keep me", handoff)
            self.assertIn("unknown: retain", handoff)
            stream_handoff = (alpha / "workstreams" / "Build" / "handoff.md").read_text(encoding="utf-8")
            self.assertIn("Review the log", stream_handoff)
            self.assertNotIn("ORIGINAL", stream_handoff)
            role.write_text("changed after migration\n", encoding="utf-8")
            original_handoff.write_text("changed handoff\n", encoding="utf-8")
            restored = session["restore_workspace"](workspace, backup, projects)
            self.assertIn("restore complete", "\n".join(restored))
            self.assertEqual(role.read_bytes(), role_bytes)
            self.assertEqual(legacy.read_bytes(), legacy_bytes)
            self.assertEqual((roles / "current_role.md").read_bytes(), selector_bytes)
            self.assertEqual(original_handoff.read_text(encoding="utf-8"), "# Handoff\n\nORIGINAL\n")
            manifest = json.loads((backup / "roles-migration" / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["roles"])
            self.assertTrue(manifest["legacy"])

    def test_upgrade_runs_migration_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            system = workspace / "bSmart-System"
            (system / "bSmart_Templates").mkdir(parents=True)
            (system / "bStart.py").write_text("new bStart\n", encoding="utf-8")
            (system / "bSmart_Templates" / "AGENTS.md").write_text("Run `python bStart.py`.\n", encoding="utf-8")
            content = workspace / "bSmart"
            content.mkdir()
            projects = workspace / "projects" / "Alpha"
            projects.mkdir(parents=True)
            roles = content / "Roles"
            roles.mkdir()
            (roles / "general_role.md").write_text(
                "active_project: Alpha\ncurrent_focus: Keep this focus\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            import sys
            old = sys.argv
            try:
                sys.argv = [str(UPGRADE), "--workspace", str(workspace), "--projects-root", str(workspace / "projects")]
                with contextlib.redirect_stdout(output):
                    self.assertEqual(upgrade["main"](), 0)
            finally:
                sys.argv = old
            report = output.getvalue()
            self.assertIn("role_migration: migrated general -> Alpha/handoff.md", report)
            self.assertIn("Keep this focus", (projects / "handoff.md").read_text(encoding="utf-8"))
            backup = next((workspace / ".bsmart-upgrade-backups").glob("*/roles-migration"))
            (roles / "general_role.md").write_text("mutated\n", encoding="utf-8")
            restore_out = io.StringIO()
            try:
                sys.argv = [
                    str(UPGRADE),
                    "--workspace",
                    str(workspace),
                    "--projects-root",
                    str(workspace / "projects"),
                    "--restore-session-projects",
                    str(backup.parent),
                ]
                with contextlib.redirect_stdout(restore_out):
                    self.assertEqual(upgrade["main"](), 0)
            finally:
                sys.argv = old
            self.assertIn("active_project: Alpha", (roles / "general_role.md").read_text(encoding="utf-8"))
            self.assertIn("restore complete", restore_out.getvalue())


if __name__ == "__main__":
    unittest.main()
