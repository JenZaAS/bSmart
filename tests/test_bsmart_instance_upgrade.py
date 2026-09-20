from __future__ import annotations

import runpy
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bsmart-instance-upgrade"

module = runpy.run_path(str(SCRIPT))


class InstanceUpgradeTests(unittest.TestCase):
    def test_repairs_existing_hook_and_installs_bstart_with_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            system = workspace / "bSmart-System"
            (system / "bSmart_Templates").mkdir(parents=True)
            source = system / "bStart.py"
            source.write_text("new bStart\n", encoding="utf-8")
            (system / "bSmart_Templates" / "AGENTS.md").write_text("Run `python bStart.py`.\n", encoding="utf-8")
            old_hook = workspace / "HERMES.md"
            old_hook.write_text("Read bSmart.md\n", encoding="utf-8")
            (workspace / "bSmart").mkdir()
            (workspace / "bSmart" / "bSmart_State.md").write_text("preserve me\n", encoding="utf-8")
            (workspace / "bSmart" / "bSmart_Agent.md").write_text("# Agent\n\n## Startup reply behavior\n- Start with `bSmart — Hi! Welcome back.`\n", encoding="utf-8")
            self.assertEqual(module["main"].__name__, "main")
            # Invoke through a temporary argv because the helper is intentionally CLI-shaped.
            import sys
            old_argv = sys.argv
            output = io.StringIO()
            try:
                sys.argv = [str(SCRIPT), "--workspace", str(workspace)]
                with contextlib.redirect_stdout(output):
                    self.assertEqual(module["main"](), 0)
            finally:
                sys.argv = old_argv
            self.assertEqual((workspace / "bStart.py").read_text(), "new bStart\n")
            self.assertEqual((workspace / "HERMES.md").read_text(), "Run `python bStart.py`.\n")
            backups = list((workspace / ".bsmart-upgrade-backups").glob("*/HERMES.md"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), "Read bSmart.md\n")
            self.assertEqual((workspace / "bSmart" / "bSmart_State.md").read_text(), "preserve me\n")
            self.assertIn("profile_review: bSmart_Agent.md contains an older startup-reply policy", output.getvalue())
            self.assertIn("approval required", output.getvalue())


if __name__ == "__main__":
    unittest.main()
