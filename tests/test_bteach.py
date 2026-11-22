"""bTeach (0.1.58): optional, user-invoked teaching extension docs."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BTEACH = ROOT / "bSmart-Extensions" / "bTeach"


def flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class BTeachDocsTest(unittest.TestCase):
    def test_files_exist(self):
        for name in ("README.md", "teach.md", "templates/course.template.md", "templates/lesson.template.md"):
            self.assertTrue((BTEACH / name).is_file(), name)
        self.assertFalse(list(BTEACH.glob("install*")), "bTeach needs no install script")

    def test_explain_is_default_with_one_check_question(self):
        text = flat(BTEACH / "teach.md")
        self.assertIn("Mode 1: explain (default)", text)
        self.assertIn("Explain one thing.", text)
        self.assertIn("Short plain sentences, at that level", text)
        self.assertIn("Find the level.", text)
        self.assertIn("Ask one short question", text)
        self.assertIn("Then stop, unless the user asks for the next part.", text)

    def test_points_to_glossary_and_adrs(self):
        text = flat(BTEACH / "teach.md")
        self.assertIn("project glossary index and the matching ADRs", text)
        self.assertIn("bSmart_Protocols/design-context.md", text)
        self.assertIn("Name the glossary entry, ADR, file, or source", text)
        self.assertTrue((ROOT / "bSmart_Protocols" / "design-context.md").is_file())

    def test_course_only_on_request_outside_repo(self):
        text = flat(BTEACH / "teach.md")
        self.assertIn("Mode 2: course (only on request)", text)
        self.assertIn("outside any product or code repo", text)
        self.assertIn("<content-root>/Workdocs/learn/<topic>/", text)
        self.assertIn("Never inside a code repo.", text)
        self.assertIn("Markdown only", text)
        for doc in ("bSmart_Map.md", "bSmart_Docs/extensions.md"):
            self.assertIn("Workdocs/learn/<topic>/", flat(ROOT / doc), doc)

    def test_never_during_a_build(self):
        text = flat(BTEACH / "teach.md")
        self.assertIn("Do not teach while a build is running: a bSwarm run, or a coding task in progress", text)
        self.assertIn("offer it then", text)
        self.assertIn("The coder never runs bTeach", text)
        self.assertIn("never gives permission to edit, build, commit, or publish", text)

    def test_registered_everywhere(self):
        self.assertIn("bTeach:\n      path: /workspace/bSmart-Extensions/bTeach", (ROOT / "bSmart.md").read_text(encoding="utf-8"))
        features = (ROOT / "bSmart_Features.md").read_text(encoding="utf-8")
        self.assertIn("### bTeach\n", features)
        self.assertIn("python ./scripts/bFeature bTeach", features)
        self.assertIn("23. bTeach", features)
        self.assertIn("## bTeach", (ROOT / "bSmart_Docs" / "extensions.md").read_text(encoding="utf-8"))
        self.assertIn("bTeach", flat(ROOT / "bSmart-Extensions" / "README.md"))
        self.assertIn("**bTeach** (`bTeach/`)", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_generic_and_light(self):
        for path in sorted(BTEACH.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.isascii(), path.name)
            low = text.lower()
            for model in ("opus", "sonnet", "gpt-", "gemini"):
                self.assertNotIn(model, low, path.name)
            self.assertNotRegex(text, r"/(home|Users)/", path.name)
        self.assertLess(len((BTEACH / "teach.md").read_text(encoding="utf-8").splitlines()), 120)

    def test_version_and_news(self):
        text = (ROOT / "bSmart_Version.md").read_text(encoding="utf-8")
        current = re.search(r"current_version: 0\.1\.(\d+)", text)
        self.assertIsNotNone(current)
        self.assertGreaterEqual(int(current.group(1)), 58)
        section = text.split("## 0.1.58-draft", 1)[1].split("\n## ", 1)[0]
        news = section.split("news: |", 1)[1].split("scope:", 1)[0]
        self.assertTrue(news.isascii())
        self.assertIn("bTeach", news)


if __name__ == "__main__":
    unittest.main()
