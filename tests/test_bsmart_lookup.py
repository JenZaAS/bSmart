from __future__ import annotations

import importlib.util
import importlib.machinery
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    loader = importlib.machinery.SourceFileLoader(f"bsmart_{name}", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BSmartLookupTests(unittest.TestCase):
    def test_bmap_retrieves_system_heading(self):
        module = load_script("bMap")
        result = module.extract_entry((ROOT / "bSmart_Map.md").read_text(encoding="utf-8"), "Instance map")
        self.assertIsNotNone(result)
        self.assertIn("bSmart_InstanceMap.md", result)

    def test_bmap_resolves_project_map_from_environment(self):
        module = load_script("bMap")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "alpha"
            project.mkdir()
            (project / "bSmart_ProjectMap.md").write_text(
                "# Alpha project map\n\n## Source layout\n\n- src: application code\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"BSMART_PROJECT_ROOT": str(root)}, clear=False):
                scope, path, item = module.resolve_scope("project", "alpha:source layout")
            self.assertEqual(scope, "project")
            self.assertEqual(path, project / "bSmart_ProjectMap.md")
            self.assertEqual(item, "source layout")
            self.assertIn("src: application code", module.extract_entry(path.read_text(encoding="utf-8"), item))

    def test_bfeature_retrieves_dreaming_card(self):
        module = load_script("bFeature")
        result = module.extract_feature((ROOT / "bSmart_Features.md").read_text(encoding="utf-8"), "Dreaming")
        self.assertIsNotNone(result)
        self.assertIn("short_description: Improve local bSmart content while you sleep.", result)

    def test_dreaming_noop_contract_is_exact(self):
        protocol = (ROOT / "bSmart_Protocols" / "dreaming.md").read_text(encoding="utf-8")
        self.assertIn("The scheduled human-facing response must be exactly: `bDreaming has nothing to report.`", protocol)
        self.assertIn("report only the new finding(s), change(s), or ask(s)", protocol)

    def test_guardrails_template_has_instance_scope_and_task_number_rule(self):
        template = (ROOT / "bSmart_Templates" / "bGuardrails.template.md").read_text(encoding="utf-8")
        self.assertIn("below bSmart_Invariants.md", template)
        self.assertIn("operator preferences and instance policy", template)
        self.assertIn("never leave `N` as a placeholder", template)
        self.assertNotIn("secret values", template)

    def test_missing_entries_are_not_fabricated(self):
        bmap = load_script("bMap")
        bfeature = load_script("bFeature")
        self.assertIsNone(bmap.extract_entry("# Map\n\n## Known\ntext", "unknown"))
        self.assertIsNone(bfeature.extract_feature("# Features\n\n### Known\ntext", "unknown"))


if __name__ == "__main__":
    unittest.main()
