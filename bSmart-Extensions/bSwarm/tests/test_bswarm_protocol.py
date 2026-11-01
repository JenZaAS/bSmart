import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class BSwarmProtocolTests(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding='utf-8')

    def yaml_block(self, text, name, indent=2):
        lines = text.splitlines()
        marker = ' ' * indent + name + ':'
        start = next((i for i, line in enumerate(lines) if line == marker), -1)
        if start < 0:
            raise AssertionError(f'missing YAML block: {marker}')
        end = len(lines)
        for i in range(start + 1, len(lines)):
            line = lines[i]
            if line.strip() and len(line) - len(line.lstrip(' ')) <= indent:
                end = i
                break
        return '\n'.join(lines[start:end])

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
        self.assertIn('workflow_keyword: cascade critic', text)
        self.assertIn('workflow: critcascade', text)
        self.assertIn('bselective: all_on', text)
        self.assertIn('max_depth: 3', text)
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
        self.assertIn('Mixed architect/worker context modes are internal experimental overrides', combined)

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
            'recommended_for_cascade',
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
        self.assertIn('stages: [architect, worker]', text)
        self.assertIn('pattern: architect_worker', text)
        self.assertIn('Shape: worker | architect -> worker', text)
        self.assertNotIn('stages: [architect, coder]', text)
        self.assertIn('Programming-only compatibility metric', text)

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
        combined = '\n'.join([
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
            'target_score: 8',
            'initial_round_budget: 10',
            'extension_rounds: 10',
            'continue_until_target: true',
            'extend by another 10 rounds' if 'extend by another 10 rounds' in combined else 'extension_rounds: 10',
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
            "without the architect's working context",
            'strict ready-to-build',
            'decisions.md',
            'Prefer a critic model distinct',
            'reduced reviewer',
            'review and update the remaining plan',
        ]:
            self.assertIn(term, text)

    def test_unspecified_bswarm_defaults_to_integrated_critic_cascade(self):
        combined = '\n'.join([
            self.read('bswarm-protocol.md'),
            self.read('templates/run-spec.yaml'),
            self.read('templates/run-record.md'),
            self.read('README.md'),
        ])
        for term in [
            'defaults to `cascade critic`',
            'architect_critic',
            'programmer_critic',
            'architect_revision',
            'architect_replan',
            'strict ready-to-build',
            'decisions.md',
            'same-model fallbacks as reduced independence',
        ]:
            self.assertIn(term, combined)

    def test_test_selection_is_risk_based_and_proportional(self):
        combined = '\n'.join([
            self.read('bswarm-protocol.md'),
            self.read('templates/run-spec.yaml'),
            self.read('templates/run-record.md'),
        ])
        for term in [
            'small_component_default_scenarios: 10',
            'scenario_count_includes_parameterized_rows: true',
            'reported_issue_regressions: always_include',
            'exclude_if: implausible_and_harmless',
            'small_component_above_default_requires_architect_rationale_and_critic_approval: true',
            'meaningful or high harm',
            'cross-product combinations',
        ]:
            self.assertIn(term, combined)

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

    def test_cascade_shorthand_always_enables_bselective_and_supports_explicit_opt_out(self):
        combined = '\n'.join([
            self.read('bswarm-protocol.md'),
            self.read('templates/run-spec.yaml'),
            self.read('README.md'),
        ])
        for term in [
            'cascade critic',
            'cascade critic audit',
            'bSelective is on for every cascade phrase',
            'ordinary (non-bSelective)',
            'design audit',
            'code audit',
            'audit_after_task',
            'automatic',
            'decision',
            'optional',
        ]:
            self.assertIn(term, combined)

    def test_jobs_package_templates_define_reopenable_report_contract(self):
        for rel in [
            'templates/jobs/SPEC.md',
            'templates/jobs/README.template.md',
            'templates/jobs/report.template.md',
            'templates/jobs/plan.template.md',
        ]:
            self.assertTrue((ROOT / rel).exists(), rel)
        combined = '\n'.join(
            self.read(rel) for rel in [
                'templates/jobs/SPEC.md',
                'templates/jobs/README.template.md',
                'templates/jobs/report.template.md',
                'templates/jobs/plan.template.md',
                'bswarm-protocol.md',
                'README.md',
                'templates/run-spec.yaml',
                'templates/run-record.md',
            ]
        )
        for term in [
            'jobs/README.md',
            'report.md',
            'plan.md',
            'Update in place',
            'External-audit bullets only',
            'Do not vendor source trees or diffs',
            'trust / not verified',
            'optional findings: count only',
        ]:
            self.assertIn(term, combined)

    def test_named_cascade_examples_never_default_to_ordinary_context(self):
        sources = [
            self.read('bswarm-protocol.md'),
            self.read('templates/run-spec.yaml'),
            self.read('README.md'),
        ]
        for text in sources:
            blocks = re.findall(
                r'(?ms)^(\s+)cascade:\n(.*?)(?=^\1\S|\Z)',
                text,
            )
            self.assertTrue(blocks, 'missing named cascade example')
            for _, block in blocks:
                self.assertNotIn('architect_context_mode: ordinary', block)
                self.assertNotIn('coder_context_mode: ordinary', block)

    def test_audit_model_list_is_instance_local_and_fail_closed(self):
        combined = '\n'.join([
            self.read('bswarm-protocol.md'),
            self.read('templates/run-spec.yaml'),
            self.read('templates/run-record.md'),
            self.read('templates/audit-models.template.yaml'),
        ])
        for term in [
            'audit_models',
            'instance-local',
            'list audit models',
            'change audit models',
            'empty list',
            'blocked until configured',
            'same model',
            'actual model id',
            'could not be launched',
        ]:
            self.assertIn(term, combined)

    def test_jobs_templates_capture_audit_findings_and_write_timing(self):
        combined = '\n'.join([
            self.read('templates/jobs/SPEC.md'),
            self.read('templates/jobs/README.template.md'),
            self.read('templates/jobs/report.template.md'),
        ])
        for term in [
            'Date',
            'Slug',
            'Commit',
            'report.md',
            'after the design audit',
            'after each architect task',
            'after the final code audit',
            'Finding:',
            'Model ID:',
            'optional findings: count only',
        ]:
            self.assertIn(term, combined)

    def test_generic_contract_fields_and_blocks(self):
        combined = "\n".join(self.read(x) for x in ['bswarm-protocol.md','templates/run-spec.yaml','templates/run-record.md','README.md'])
        for field in ['criterion_or_claim','evidence_or_check','expected_signal','actual_result','reference']:
            self.assertIn(field, combined)
        self.assertIn('score >= 8 AND critical_issues == 0 AND required_changes == 0', combined)
        self.assertIn('initial_round_range: [1, 10]', combined)
        self.assertIn('extension_block_size: 10', combined)
        self.assertIn('larger_scope_numeric_cap: none', combined)
        self.assertIn('max_depth: 1 | 2 | 3', self.read('bswarm-protocol.md'))
        self.assertIn('roles: [architect, architect_critic, worker, worker_critic]', self.read('templates/run-spec.yaml'))


    def test_scoped_review_contracts(self):
        spec = self.read('templates/run-spec.yaml')
        record = self.read('templates/run-record.md')
        protocol = self.read('bswarm-protocol.md')
        for field in ['stop_requires_no_required_issues: true', 'no_hard_round_cap: true', 'workflow_selection:', 'verification_policy:', 'programming_aliases:', 'larger_scope_numeric_cap: none']:
            self.assertIn(field, spec)
        conjunction = 'score >= 8 AND critical_issues == 0 AND required_changes == 0'
        self.assertIn(conjunction, spec)
        self.assertIn(conjunction, record)
        self.assertIn('stop_requires_no_required_issues: true', record)
        self.assertIn('| criterion_or_claim | evidence_or_check | expected_signal | actual_result | reference |', record)
        self.assertIn('architect_revision/readiness', protocol)
        self.assertNotIn('architect_replan → next_task', protocol)
        self.assertIn('coder: worker', spec)

    def test_final_generic_selection_evidence_and_critique_contracts(self):
        spec = self.read('templates/run-spec.yaml')
        record = self.read('templates/run-record.md')
        protocol = self.read('bswarm-protocol.md')
        readme = self.read('README.md')
        conjunction = 'score >= 8 AND critical_issues == 0 AND required_changes == 0'
        for text in (spec, record, protocol):
            self.assertIn(conjunction, text)
            self.assertIn('stop_requires_no_critical_issues: true', text)
            self.assertIn('stop_requires_no_required_issues: true', text)
        for field in ['criterion_or_claim', 'evidence_or_check', 'expected_signal', 'actual_result', 'reference']:
            self.assertIn(field, spec)
            self.assertIn(field, record)
            self.assertIn(field, protocol)
        self.assertIn('initial_round_range: [1, 10]', spec)
        self.assertIn('extension_block_size: 10', spec)
        self.assertIn('zero_progress_at_block_end: record_plateau_and_pause_ask', spec)
        self.assertIn('safety_blocker: stop_immediately', spec)
        self.assertIn('larger_scope_numeric_cap: none', spec)
        self.assertIn('critic_cascade_if:', spec)
        self.assertIn('ask_operator_if_unclear: true', spec)
        self.assertIn('coder: worker', spec)
        self.assertIn('programmer_critic: worker_critic', spec)
        self.assertIn('coder_fix: worker_revision', spec)
        cascade = self.yaml_block(readme, 'cascade')
        self.assertIn('architect_context_mode: bselective', cascade)
        self.assertNotIn('architect_context_mode: ordinary', cascade)
        normalized = self.yaml_block(spec, 'keyword_normalization')
        self.assertIn('      worker_context_mode: bselective', normalized)
        self.assertNotIn('coder_context_mode', normalized)
        loop = self.yaml_block(spec, 'critique_loop')
        loop_keys = re.findall(r'^    ([a-z_]+):', loop, re.MULTILINE)
        self.assertEqual(len(loop_keys), len(set(loop_keys)))
        for field in [
            '    target_score: 8',
            '    stop_requires_no_critical_issues: true',
            '    stop_requires_no_required_issues: true',
            '    success_condition: "score >= 8 AND critical_issues == 0 AND required_changes == 0"',
            '    initial_round_range: [1, 10]',
            '    extension_block_size: 10',
            '    no_hard_round_cap: true',
        ]:
            self.assertIn(field, loop)
        roles = self.yaml_block(spec, 'role_defaults')
        for role in ['worker:', 'worker_critic:', 'worker_revision:', 'architect_critic:', 'architect_revision:', 'architect_replan:']:
            self.assertIn(f'    {role}', roles)
        selection = self.yaml_block(spec, 'workflow_selection')
        self.assertIn('      - multiple_or_dependent_tasks', selection)
        self.assertIn('      - unresolved_design_uncertainty', selection)
        self.assertIn('      - meaningful_risk', selection)
        testing = self.yaml_block(spec, 'testing_policy')
        self.assertIn('    small_component_default_scenarios: 10', testing)
        self.assertIn('    small_component_above_default_requires_architect_rationale_and_critic_approval: true', testing)
        self.assertIn('    larger_scope_numeric_cap: none', testing)
        aliases = self.yaml_block(spec, 'programming_aliases')
        self.assertIn('    coder: worker', aliases)
        self.assertIn('    programmer_critic: worker_critic', aliases)
        self.assertIn('    coder_fix: worker_revision', aliases)
        self.assertIn('critique_loop rounds are not capped', spec)
        self.assertIn('no_hard_round_cap: true', record)
        self.assertIn('| Block | Round range | Progress events (count) | Evidence/reference | Decision |', record)
        self.assertIn('For one bounded low-risk deliverable', protocol)
        self.assertIn('unresolved design uncertainty', protocol)
        self.assertIn('meaningful risk', protocol)
        self.assertIn('| criterion_or_claim | evidence_or_check | expected_signal | actual_result | reference |', record)
        self.assertIn('[programming-only] expected UI scaffolding strings', record)
        self.assertIn('role: architect | architect_critic | architect_revision | worker | worker_critic | worker_revision | architect_replan | supervisor', protocol)
        self.assertIn('architect_revision/readiness', protocol)
        self.assertNotIn('next_task', protocol)

if __name__ == '__main__':
    unittest.main()
