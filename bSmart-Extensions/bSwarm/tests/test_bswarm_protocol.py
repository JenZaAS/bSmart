import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class BSwarmProtocolTests(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding='utf-8')

    def test_required_files_exist(self):
        for rel in [
            'README.md',
            'bswarm-protocol.md',
            'templates/run-spec.yaml',
            'templates/run-record.md',
        ]:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_run_spec_defaults_are_bounded(self):
        text = self.read('templates/run-spec.yaml')
        self.assertIn('mode: unsupervised', text)
        self.assertIn('statistics: on', text)
        self.assertIn('max_depth: 1', text)
        self.assertIn('max_total_child_agents: 3', text)
        self.assertIn('max_iterations: 5', text)
        self.assertIn('max_worker_attempts_per_supervisor: 5', text)
        self.assertNotIn('unbounded', text.lower())

    def test_protocol_names_modes_and_ab_styles(self):
        text = self.read('bswarm-protocol.md')
        for term in ['unsupervised', 'supervised', 'report', 'self_improving', 'all_off', 'all_on', 'mixed_ab']:
            self.assertIn(term, text)

    def test_protocol_requires_concise_outputs_and_no_nested_swarm(self):
        text = self.read('bswarm-protocol.md').lower()
        self.assertIn('never launch another bswarm', text)
        self.assertRegex(text, re.compile(r'1-3 bullets|quick-glance'))

    def test_run_record_has_quick_summary_and_stats(self):
        text = self.read('templates/run-record.md')
        for section in ['## Summary', '## Statistics', '## Branch results', '## Evidence', '## Verification']:
            self.assertIn(section, text)

if __name__ == '__main__':
    unittest.main()
