import json
import tempfile
import unittest
from pathlib import Path

from bqabuild_handler import (
    answer_question,
    build_brief,
    load_session,
    next_question,
    revise_answer,
    set_questions,
    start_session,
)


QUESTIONS = [
    {
        "id": "storage",
        "title": "Where should state live?",
        "context": "The state must survive a session restart.",
        "options": ["Project-local", "Instance-local"],
        "recommendation": "Instance-local",
    },
    {
        "id": "scope",
        "title": "What is the first release scope?",
        "options": ["Prototype", "Production-ready"],
        "recommendation": "Prototype",
    },
]


class BQABuildTests(unittest.TestCase):
    def test_session_lifecycle_records_answers_and_builds_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = start_session("Add export support", root=root, session_id="export")
            questions_file = root / "questions.json"
            questions_file.write_text(json.dumps(QUESTIONS), encoding="utf-8")
            set_questions("export", questions_file, root=root)

            first_question = next_question("export", root=root)
            if first_question is None:
                self.fail("Expected first question")
            self.assertEqual(first_question["id"], "storage")
            answer_question("export", "Instance-local", root=root)
            second_question = next_question("export", root=root)
            if second_question is None:
                self.fail("Expected second question")
            self.assertEqual(second_question["id"], "scope")
            answer_question("export", "Prototype", root=root)

            brief = build_brief(
                "export",
                read_first=["project.md"],
                steps=["Add the handler"],
                validations=["Run unit tests"],
                rules=["Do not deploy"],
                root=root,
            )
            loaded = load_session(root, "export")
            text = brief.read_text(encoding="utf-8")

        self.assertEqual(session["status"], "draft")
        self.assertEqual(loaded["status"], "built")
        self.assertEqual(len(loaded["answers"]), 2)
        self.assertIn("Instance-local", text)
        self.assertIn("Add the handler", text)
        self.assertIn("Do not deploy", text)
        self.assertIn("not authorization", text)

    def test_cannot_build_before_all_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            start_session("Incomplete", root=root, session_id="incomplete")
            questions_file = root / "questions.json"
            questions_file.write_text(json.dumps(QUESTIONS), encoding="utf-8")
            set_questions("incomplete", questions_file, root=root)
            answer_question("incomplete", "Project-local", root=root)

            with self.assertRaises(ValueError):
                build_brief("incomplete", root=root)

    def test_revision_appends_and_marks_superseded_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            start_session("Revision", root=root, session_id="revision")
            questions_file = root / "questions.json"
            questions_file.write_text(json.dumps(QUESTIONS), encoding="utf-8")
            set_questions("revision", questions_file, root=root)
            answer_question("revision", "Project-local", root=root)
            revised = revise_answer("revision", "storage", "Instance-local", root=root)

        self.assertEqual(len(revised["answers"]), 2)
        self.assertEqual(revised["answers"][-1]["answer"], "Instance-local")
        self.assertIn("supersedes_recorded_at_utc", revised["answers"][-1])

    def test_question_validation_rejects_duplicate_ids_and_bad_option_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            start_session("Invalid", root=root, session_id="invalid")
            questions_file = root / "questions.json"
            questions_file.write_text(
                json.dumps([
                    {"id": "same", "title": "One", "options": ["A"], "recommendation": "A"},
                ]),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                set_questions("invalid", questions_file, root=root)


if __name__ == "__main__":
    unittest.main()
