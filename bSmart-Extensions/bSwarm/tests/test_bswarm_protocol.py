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

    def test_compact_workflow_keywords_are_normalized(self):
        combined = '\n'.join([
            self.read('bswarm-protocol.md'),
            self.read('templates/run-spec.yaml'),
            self.read('README.md'),
        ])
        for term in [
            'workflow_keyword',
            'ordinary',
            'bSelective',
            'architect',
            'bSelective architect',
            'cascade',
            'bSelective cascade',
            'workflow: direct',
            'workflow: architect_handoff',
            'workflow: architect_taskflow',
            'coder_context_mode: bselective',
            'max_tasks: 4',
            're_evaluate_after_each_task: true',
        ]:
            self.assertIn(term, combined)
        self.assertIn('Mixed architect/coder context modes are internal experimental overrides', combined)

    def test_architect_and_cascade_preflight_qc_checks_runtime_adapter_and_hermes_settings(self):
        combined = '\n'.join([
            self.read('bswarm-protocol.md'),
            self.read('templates/run-spec.yaml'),
            self.read('templates/run-record.md'),
            self.read('README.md'),
        ])
        for term in [
            'Preflight QC',
            'preflight_qc',
            'adapter: hermes',
            'opencode',
            'delegation.orchestrator_enabled',
            'delegation.max_spawn_depth',
            'delegation.child_timeout_seconds',
            'planned_timeout_seconds: 1200',
            'required_for_nested_architect_dispatch',
            'recommended_for_bselective_cascade',
            'supervisor_mediated_architect_handoff',
            'supervisor_mediated_cascade',
            'stop_for_settings',
            'downgrade_to_supervisor_mediated_architect_handoff',
            'downgrade_to_supervisor_mediated_cascade',
        ]:
            self.assertIn(term, combined)
        self.assertRegex(combined, re.compile(r'max_spawn_depth.*>= 2', re.DOTALL))

    def test_protocol_requires_concise_outputs_and_no_nested_swarm(self):
        text = self.read('bswarm-protocol.md').lower()
        self.assertIn('never launch another bswarm', text)
        self.assertRegex(text, re.compile(r'1-3 bullets|quick-glance'))

    def test_run_record_has_quick_summary_and_stats(self):
        text = self.read('templates/run-record.md')
        for section in ['## Summary', '## Statistics', '## Branch results', '## Evidence', '## Verification']:
            self.assertIn(section, text)

    def test_run_spec_supports_direct_and_architect_coder_branches(self):
        text = self.read('templates/run-spec.yaml')
        for term in [
            'branches:',
            'ordinary:',
            'pattern: direct_worker',
            'bselective:',
            'architect:',
            'bselective_architect:',
            'cascade:',
            'bselective_cascade:',
            'pattern: architect_coder',
            'pattern: architect_taskflow',
            'architect_context_mode: bselective',
            'architect_context_mode: ordinary',
            'coder_context_mode: bselective',
            'coder_context_mode: ordinary',
            '- architect',
            '- coder',
            '- architect_evaluation',
        ]:
            self.assertIn(term, text)

    def test_protocol_defines_supervisor_architect_coder_semantics(self):
        text = self.read('bswarm-protocol.md').lower()
        for term in [
            'supervisor mode',
            'architect mode',
            'coder mode',
            'does not directly edit target implementation files',
            'must not edit implementation files',
            'edits only the branch duplicate file',
            'do not include previous generated-run paths',
            'previous-generated-runs',
            'architect-plan.md',
            'stats-index.md',
        ]:
            self.assertIn(term, text)

    def test_run_record_separates_stage_and_branch_statistics(self):
        text = self.read('templates/run-record.md')
        for term in [
            '## Stage statistics',
            '## Branch total statistics',
            'architect-plan.md',
            'fresh_total_tokens',
            'total_with_cache_read_tokens',
            'diff_added_lines',
            'matlab_runtime_verification',
        ]:
            self.assertIn(term, text)

    def test_readme_documents_abc_architect_coder_usage(self):
        text = self.read('README.md')
        for term in [
            'supervisor',
            'architect',
            'coder',
            'bselective_architect',
            'bselective_cascade',
            'direct_worker',
            'architect_taskflow',
        ]:
            self.assertIn(term, text)

    def test_critcascade_contract_is_depth_three_and_stepwise(self):
        combined = '\\n'.join([
            self.read('bswarm-protocol.md'),
            self.read('templates/run-spec.yaml'),
            self.read('templates/run-record.md'),
            self.read('README.md'),
        ])
        for term in [
            'critcascade',
            'max_depth: 3',
            'architect_critic',
            'programmer_critic',
            'score: 1-10',
            'bKnowledge',
            'one task at a time',
            'review and update the remaining plan',
            'stop at 8 or higher',
            'max_critique_rounds: 3',
        ]:
            self.assertIn(term, combined)

    def test_critcascade_has_concise_critic_contract_and_knowledge_rules(self):
        text = self.read('bswarm-protocol.md')
        for term in [
            'critical_issues',
            'important_issues',
            'required_changes',
            'verification_needed',
            'general knowledge',
            'concise durable lessons',
            'must not edit implementation files',
        ]:
            self.assertIn(term, text)

    def test_architect_handoff_defaults_are_compact_and_token_aware(self):
        protocol = self.read('bswarm-protocol.md').lower()
        run_spec = self.read('templates/run-spec.yaml').lower()
        run_record = self.read('templates/run-record.md').lower()
        readme = self.read('README.md').lower()
        combined = '\n'.join([protocol, run_spec, run_record, readme])
        for term in [
            'default architect handoff budget',
            'target_words: 350-500',
            'hard_max_words: 700',
            'max_relevant_regions: 6',
            'max_must_implement_bullets: 6',
            'no_tool_transcripts: true',
            'no_long_source_quotes: true',
            'no_full_bselective_output: true',
            'must_implement',
            'defer',
            'do_not_implement',
            'context-budget artifact',
        ]:
            self.assertIn(term, combined)

if __name__ == '__main__':
    unittest.main()
