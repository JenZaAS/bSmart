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
            self.assertNotIn("custom_note", handoff)
            self.assertNotIn("unknown:", handoff)
            review = (content / "State" / "role-migration-review.md").read_text(encoding="utf-8")
            self.assertIn("custom_note: keep me", review)
            self.assertIn("unknown: retain", review)
            self.assertIn("custom_note: keep me", (backup / "roles-migration" / "review.md").read_text(encoding="utf-8"))
            stream_handoff = (alpha / "workstreams" / "Build" / "handoff.md").read_text(encoding="utf-8")
            self.assertIn("Review the log", stream_handoff)
            self.assertNotIn("ORIGINAL", stream_handoff)
            role.write_text("changed after migration\n", encoding="utf-8")
            role.chmod(0o444)
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

    def test_non_utf8_handoff_keeps_a_manifest_and_can_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            content = workspace / "bSmart"
            roles = content / "Roles"
            roles.mkdir(parents=True)
            projects = workspace / "projects"
            alpha = projects / "Alpha"
            beta = projects / "Beta"
            alpha.mkdir(parents=True)
            beta.mkdir()
            (alpha / "handoff.md").write_text("# Handoff\n\nAlpha\n", encoding="utf-8")
            beta_bytes = "Beta caf\xe9\n".encode("cp1252")
            (beta / "handoff.md").write_bytes(beta_bytes)
            (roles / "alpha_role.md").write_text("active_project: Alpha\ncurrent_focus: Keep alpha\n", encoding="utf-8")
            (roles / "beta_role.md").write_text("active_project: Beta\ncurrent_focus: Keep beta\n", encoding="utf-8")
            backup = workspace / ".bsmart-upgrade-backups" / "stamp"
            report = "\n".join(session["migrate_workspace"](workspace, backup, projects))
            self.assertIn("migrated alpha -> Alpha/handoff.md", report)
            self.assertIn("not UTF-8", report)
            self.assertTrue((backup / "roles-migration" / "manifest.json").is_file())
            self.assertEqual((beta / "handoff.md").read_bytes(), beta_bytes)
            self.assertIn("Keep alpha", (alpha / "handoff.md").read_text(encoding="utf-8"))
            restored = "\n".join(session["restore_workspace"](workspace, backup, projects))
            self.assertIn("restore complete", restored)
            self.assertEqual((beta / "handoff.md").read_bytes(), beta_bytes)
            self.assertEqual((alpha / "handoff.md").read_text(encoding="utf-8"), "# Handoff\n\nAlpha\n")

    def test_later_notes_survive_a_second_migrate_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            content = workspace / "bSmart"
            roles = content / "Roles"
            roles.mkdir(parents=True)
            projects = workspace / "projects" / "Alpha"
            projects.mkdir(parents=True)
            handoff = projects / "handoff.md"
            handoff.write_text("# Handoff\n\nORIGINAL\n", encoding="utf-8")
            (roles / "developer_role.md").write_text("active_project: Alpha\ncurrent_focus: Ship\n", encoding="utf-8")
            first = workspace / ".bsmart-upgrade-backups" / "first"
            session["migrate_workspace"](workspace, first, workspace / "projects")
            handoff.write_text(handoff.read_text(encoding="utf-8") + "REAL NOTES\n", encoding="utf-8")
            second = workspace / ".bsmart-upgrade-backups" / "second"
            again = "\n".join(session["migrate_workspace"](workspace, second, workspace / "projects"))
            self.assertIn("already migrated", again)
            self.assertFalse((second / "roles-migration").exists())
            self.assertIn("REAL NOTES", handoff.read_text(encoding="utf-8"))
            restored = "\n".join(session["restore_workspace"](workspace, first, workspace / "projects"))
            self.assertIn("kept Alpha/handoff.md", restored)
            self.assertIn("REAL NOTES", handoff.read_text(encoding="utf-8"))
            self.assertIn("Ship", handoff.read_text(encoding="utf-8"))

    def test_upgrade_catches_a_decode_error(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            system = workspace / "bSmart-System"
            (system / "bSmart_Templates").mkdir(parents=True)
            (system / "bStart.py").write_text("new bStart\n", encoding="utf-8")
            (system / "bSmart_Templates" / "AGENTS.md").write_text("Run `python bStart.py`.\n", encoding="utf-8")
            (workspace / "bSmart").mkdir()
            original = upgrade["main"].__globals__["migrate_workspace"]

            def boom(*_args, **_kwargs):
                raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

            upgrade["main"].__globals__["migrate_workspace"] = boom
            output = io.StringIO()
            import sys
            old = sys.argv
            try:
                sys.argv = [str(UPGRADE), "--workspace", str(workspace)]
                with contextlib.redirect_stdout(output):
                    code = upgrade["main"]()
            finally:
                sys.argv = old
                upgrade["main"].__globals__["migrate_workspace"] = original
            self.assertEqual(code, 1)
            self.assertIn("role_migration: blocked", output.getvalue())
            self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
