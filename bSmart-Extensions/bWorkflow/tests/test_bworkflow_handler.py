import tempfile
import unittest
from pathlib import Path

from bworkflow_handler import (
    get_workflow,
    get_workflow_section,
    list_workflows,
    log_workflow_run,
    reset_workflow_counters,
    search_workflows,
)


def write_sample_catalogue(root: Path) -> None:
    (root / "index.md").write_text(
        "# Workflow catalogue\n\n"
        "trust_thresholds:\n"
        "  alpha_to_beta:\n"
        "    min_total_runs: 10\n"
        "    min_success_rate: 0.80\n\n"
        "## Domains\n\n"
        "- ID: mathworks\n"
        "  Path: mathworks/\n"
        "  Title: MathWorks workflows\n"
        "  Summary: MATLAB and MathWorks procedures.\n"
        "  Keywords: matlab, mathworks\n",
        encoding="utf-8",
    )
    (root / "mathworks").mkdir()
    (root / "mathworks" / "index.md").write_text(
        "# MathWorks workflow catalogue\n\n"
        "## Topics\n\n"
        "- ID: mathworks.segy\n"
        "  Path: segy.md\n"
        "  Title: SEG-Y workflows\n"
        "  Summary: Procedures for SEG-Y files.\n"
        "  Keywords: segy, headers\n",
        encoding="utf-8",
    )
    (root / "mathworks" / "segy.md").write_text(
        "# SEG-Y workflows\n\n"
        "This file is part of bWorkflow feature in bSmart.\n\n"
        "Catalogue metadata for this file is maintained in `index.md` one level up.\n\n"
        "## WORKFLOW mathworks.segy.load\n\n"
        "ID: mathworks.segy.load\n"
        "Title: Load SEG-Y data\n"
        "Status: alpha-new\n"
        "Status since: 2026-08-20\n"
        "Successful runs: 0\n"
        "Failed runs: 0\n"
        "Total runs: 0\n"
        "Last successful use: None\n"
        "Last failed use: None\n"
        "Associated files:\n"
        "  - libs/segy/SegyFile.m\n\n"
        "### Purpose\n\n"
        "Load SEG-Y files through the standard SegyFile API.\n\n"
        "### Preconditions\n\n"
        "None.\n\n"
        "### Steps\n\n"
        "1. Create a SegyFile object.\n"
        "2. Call loadSegy.\n\n"
        "### Verification\n\n"
        "Confirm traces and headers load.\n",
        encoding="utf-8",
    )

class BWorkflowHandlerTests(unittest.TestCase):
    def test_list_workflows_without_scope_lists_top_level_domains(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            result = list_workflows(root=root)

        self.assertEqual(
            result,
            [
                {
                    "id": "mathworks",
                    "path": "mathworks/",
                    "title": "MathWorks workflows",
                    "summary": "MATLAB and MathWorks procedures.",
                    "keywords": ["matlab", "mathworks"],
                    "type": "domain",
                }
            ],
        )

    def test_list_workflows_with_domain_scope_lists_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            result = list_workflows("mathworks", root=root)

        self.assertEqual(
            result,
            [
                {
                    "id": "mathworks.segy",
                    "path": "segy.md",
                    "title": "SEG-Y workflows",
                    "summary": "Procedures for SEG-Y files.",
                    "keywords": ["segy", "headers"],
                    "type": "topic",
                }
            ],
        )
    def test_list_workflows_with_topic_scope_lists_workflow_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            result = list_workflows("mathworks.segy", root=root)

        self.assertEqual(
            result,
            [
                {
                    "id": "mathworks.segy.load",
                    "type": "workflow",
                    "title": "Load SEG-Y data",
                    "status": "alpha-new",
                    "status_since": "2026-08-20",
                    "successful_runs": "0",
                    "failed_runs": "0",
                    "total_runs": "0",
                    "last_successful_use": "None",
                    "last_failed_use": "None",
                    "associated_files": ["libs/segy/SegyFile.m"],
                }
            ],
        )
    def test_list_workflows_filter_matches_title_summary_id_and_keywords(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            result = list_workflows("mathworks", filter="headers", root=root)

        self.assertEqual([item["id"] for item in result], ["mathworks.segy"])

    def test_get_workflow_with_topic_id_returns_whole_topic_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            text = get_workflow("mathworks.segy", root=root)

        self.assertIn("# SEG-Y workflows", text)
        self.assertIn("## WORKFLOW mathworks.segy.load", text)

    def test_get_workflow_with_entry_id_returns_only_that_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            text = get_workflow("mathworks.segy.load", root=root)

        self.assertTrue(text.startswith("## WORKFLOW mathworks.segy.load"))
        self.assertIn("### Steps", text)
        self.assertNotIn("# SEG-Y workflows", text)

    def test_get_workflow_section_returns_named_section_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            text = get_workflow_section("mathworks.segy.load", "Steps", root=root)

        self.assertEqual(text.strip(), "1. Create a SegyFile object.\n2. Call loadSegy.")

    def test_search_workflows_finds_by_associated_file_and_keyword(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            by_file = search_workflows(associated_file="SegyFile.m", root=root)
            by_keyword = search_workflows(query="headers", root=root)

        self.assertEqual([item["id"] for item in by_file], ["mathworks.segy.load"])
        self.assertEqual([item["id"] for item in by_keyword], ["mathworks.segy"])

    def test_log_workflow_run_updates_success_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            updated = log_workflow_run(
                "mathworks.segy.load",
                "success",
                root=root,
                date="2026-08-20",
            )
            text = get_workflow("mathworks.segy.load", root=root)

        self.assertEqual(updated["successful_runs"], "1")
        self.assertIn("Successful runs: 1", text)
        self.assertIn("Total runs: 1", text)
        self.assertIn("Last successful use: 2026-08-20", text)

    def test_reset_workflow_counters_zeros_status_period_and_adds_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_sample_catalogue(root)
            log_workflow_run("mathworks.segy.load", "failure", root=root, date="2026-08-20")
            reset = reset_workflow_counters(
                "mathworks.segy.load",
                reason="Updated workflow after API fix.",
                root=root,
                date="2026-08-21",
                git_commit="abc123",
            )
            text = get_workflow("mathworks.segy.load", root=root)

        self.assertEqual(reset["total_runs"], "0")
        self.assertIn("Failed runs: 0", text)
        self.assertIn("Last failed use: None", text)
        self.assertIn("2026-08-21 — counters reset", text)
        self.assertIn("Git commit: abc123", text)


if __name__ == "__main__":
    unittest.main()
