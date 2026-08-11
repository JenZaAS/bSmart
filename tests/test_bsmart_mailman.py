import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB_PATH = ROOT / "scripts" / "bsmart_mailman_lib.py"
BMAIL = ROOT / "scripts" / "bMail"
MAILMAN = ROOT / "scripts" / "bsmart-mailman"


def load_module():
    spec = importlib.util.spec_from_file_location("bsmart_mailman_lib", LIB_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BSmartMailmanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fm = self.root / "FM" / "mail"
        self.admin = self.root / "Admin" / "mail"
        self.registry = self.root / "registry.json"
        self.registry.write_text(json.dumps({
            "agents": {
                "FM": {
                    "display_name": "First Mate",
                    "role": "Coordinator agent",
                    "description": "Routes work to Admin.",
                    "mailbox": str(self.fm),
                    "send_policy": {"mode": "restricted", "allow_to": ["Admin"], "deny_to": []},
                    "wake": {"type": "none"},
                },
                "Admin": {
                    "display_name": "Admin",
                    "role": "Administrative agent",
                    "description": "Receives mail and approves protected integrations.",
                    "mailbox": str(self.admin),
                    "send_policy": {"mode": "restricted", "allow_to": [], "deny_to": []},
                    "wake": {"type": "file", "handling_hint": "triage_then_delegate"},
                },
            },
            "routes": {"default_policy": "deny"},
        }), encoding="utf-8")
        self.module = load_module()
        self.module.init_mailbox(self.fm)
        self.module.init_mailbox(self.admin)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, expect=0):
        proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, expect, msg=f"stdout={proc.stdout}\nstderr={proc.stderr}")
        return proc

    def test_allowed_delivery_moves_sender_to_sent_and_recipient_to_new(self):
        queued = self.module.send_message(self.registry, "FM", "Admin", "Hello", "Body")
        counts = self.module.deliver(self.registry)
        self.assertEqual(counts["delivered"], 1)
        self.assertFalse(queued.exists())
        sent = list((self.fm / "outbox" / "sent").glob("*.json"))
        new = list((self.admin / "inbox" / "new").glob("*.json"))
        self.assertEqual(len(sent), 1)
        self.assertEqual(len(new), 1)
        delivered = json.loads(new[0].read_text(encoding="utf-8"))
        self.assertEqual(delivered["from"], "FM")
        self.assertEqual(delivered["to"], "Admin")
        self.assertTrue((self.fm / "log" / "deliveries.jsonl").exists())
        self.assertTrue((self.admin / "log" / "deliveries.jsonl").exists())
        wake = list((self.admin / "wake" / "pending").glob("*.json"))
        self.assertEqual(len(wake), 1)
        wake_marker = json.loads(wake[0].read_text(encoding="utf-8"))
        self.assertEqual(wake_marker["type"], "mail_arrived")
        self.assertEqual(wake_marker["handling_hint"], "triage_then_delegate")

    def test_denied_route_moves_to_failed_and_does_not_deliver(self):
        queued = self.module.send_message(self.registry, "Admin", "FM", "No", "Denied")
        counts = self.module.deliver(self.registry)
        self.assertEqual(counts["failed"], 1)
        self.assertFalse(queued.exists())
        self.assertEqual(list((self.fm / "inbox" / "new").glob("*.json")), [])
        failed = list((self.admin / "outbox" / "failed").glob("*.json"))
        self.assertEqual(len(failed), 1)
        failed_msg = json.loads(failed[0].read_text(encoding="utf-8"))
        self.assertIn("route denied", failed_msg["delivery_error"])

    def test_read_moves_new_message_to_read(self):
        self.module.send_message(self.registry, "FM", "Admin", "Read me", "Body")
        self.module.deliver(self.registry)
        msg_id = json.loads(next((self.admin / "inbox" / "new").glob("*.json")).read_text(encoding="utf-8"))["id"]
        message = self.module.read_message(self.admin, msg_id)
        self.assertEqual(message["subject"], "Read me")
        self.assertEqual(list((self.admin / "inbox" / "new").glob("*.json")), [])
        self.assertEqual(len(list((self.admin / "inbox" / "read").glob("*.json"))), 1)

    def test_cli_send_inbox_and_deliver(self):
        self.run_cli(sys.executable, str(BMAIL), "send", "--registry", str(self.registry), "--from", "FM", "--to", "Admin", "--subject", "CLI", "--body", "Hi")
        self.run_cli(sys.executable, str(MAILMAN), "deliver", "--registry", str(self.registry))
        inbox = self.run_cli(sys.executable, str(BMAIL), "inbox", "--mailbox", str(self.admin))
        self.assertIn('"subject": "CLI"', inbox.stdout)

    def test_cli_check_summarizes_messages_and_wake_markers(self):
        self.module.send_message(self.registry, "FM", "Admin", "Check me", "Body")
        self.module.deliver(self.registry)
        check = self.run_cli(sys.executable, str(BMAIL), "check", "--mailbox", str(self.admin), expect=1)
        summary = json.loads(check.stdout)
        self.assertEqual(summary["new"], 1)
        self.assertEqual(summary["wake_pending"], 1)
        self.assertEqual(summary["messages"][0]["subject"], "Check me")
        self.assertEqual(summary["wake"][0]["type"], "mail_arrived")

    def test_send_policy_open_with_deny_exception_blocks_recipient(self):
        data = json.loads(self.registry.read_text(encoding="utf-8"))
        data["agents"]["Admin"]["send_policy"] = {"mode": "open", "allow_to": [], "deny_to": ["FM"]}
        self.registry.write_text(json.dumps(data), encoding="utf-8")
        queued = self.module.send_message(self.registry, "Admin", "FM", "Blocked", "Denied by exception")
        counts = self.module.deliver(self.registry)
        self.assertEqual(counts["failed"], 1)
        failed_msg = json.loads(next((self.admin / "outbox" / "failed").glob("*.json")).read_text(encoding="utf-8"))
        self.assertIn("deny_to", failed_msg["delivery_error"])
        self.assertFalse(queued.exists())

    def test_send_policy_disabled_cannot_be_overridden_by_allow_to(self):
        data = json.loads(self.registry.read_text(encoding="utf-8"))
        data["agents"]["FM"]["send_policy"] = {"mode": "disabled", "allow_to": ["Admin"], "deny_to": []}
        self.registry.write_text(json.dumps(data), encoding="utf-8")
        self.module.send_message(self.registry, "FM", "Admin", "Blocked", "Disabled")
        counts = self.module.deliver(self.registry)
        self.assertEqual(counts["failed"], 1)
        failed_msg = json.loads(next((self.fm / "outbox" / "failed").glob("*.json")).read_text(encoding="utf-8"))
        self.assertIn("disabled", failed_msg["delivery_error"])

    def test_cli_can_record_intent_goal_and_subagent_id(self):
        self.run_cli(
            sys.executable, str(BMAIL), "send",
            "--registry", str(self.registry),
            "--from", "FM", "--to", "Admin",
            "--subject", "Delegated result",
            "--intent", "Answer incoming DigTech mail",
            "--goal", "Send a concise resolved reply",
            "--handled-by", "subagent-20260811-demo",
            "--body", "Done",
        )
        self.run_cli(sys.executable, str(MAILMAN), "deliver", "--registry", str(self.registry))
        delivered = json.loads(next((self.admin / "inbox" / "new").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(delivered["intent"], "Answer incoming DigTech mail")
        self.assertEqual(delivered["goal"], "Send a concise resolved reply")
        self.assertEqual(delivered["handled_by"], "subagent-20260811-demo")


if __name__ == "__main__":
    unittest.main()
