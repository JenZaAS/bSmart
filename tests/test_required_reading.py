import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXT = ROOT / 'bSmart-Extensions'
BSWARM = EXT / 'bSwarm'
SHAPE_KEYS = ['required_context:', 'revision_or_sha256:', 'applicable_requirements:',
              'not_applicable_with_reason:', 'unresolved_conflicts:', 'coder_checks:',
              'critic_compliance:']


def read(path):
    # Collapse whitespace so wrapped Markdown lines still match.
    return ' '.join(path.read_text(encoding='utf-8').split())


class RequiredReadingTests(unittest.TestCase):
    def test_project_rule_and_core_pointer(self):
        projects = read(ROOT / 'bSmart_Protocols' / 'projects.md')
        for term in ['required_reading_bundle:', 'Required reading bundle',
                     'report the missing path', 'Not a block. Continue the task',
                     'Not migrated', 'Check only these two places',
                     'Do not search elsewhere for guidance the project has not declared',
                     'Mandatory for architect, coder, and critic',
                     "required_reading_bundle field in the project's project.md",
                     'required_reading_bundle: [<path relative to the project>, ...]']:
            self.assertIn(term, projects)
        core = read(ROOT / 'bSmart.md')
        self.assertIn('required_reading:', core)
        self.assertIn('required_reading_bundle in bSmart_Protocols/projects.md', core)

    def test_template_section_is_empty(self):
        text = (ROOT / 'bSmart_Templates' / 'project-task-context-routing.template.md').read_text(encoding='utf-8')
        self.assertIn('## Required reading bundle', text)
        section = text.split('## Required reading bundle', 1)[1].split('\n## ', 1)[0]
        # Guidance and a commented example only: no listed file.
        listed = [ln for ln in section.splitlines() if ln.startswith('- ')]
        self.assertEqual(listed, [])

    def test_roles_carry_their_step(self):
        architect = read(EXT / 'bArchitect' / 'architect.md')
        self.assertIn('## Required reading acknowledgement', architect)
        self.assertIn('read it again', architect)
        self.assertIn('Required reading (hard rule)', architect)
        coder = read(EXT / 'bCoder' / 'coder.md')
        self.assertIn('Required reading (hard rule)', coder)
        self.assertIn('stop and report it; do not make up the architecture', coder)
        self.assertIn('Without a plan: read the bundle yourself', coder)
        critic = read(EXT / 'bCritic' / 'critic.md')
        self.assertIn('is a HOLD (below)', critic)
        for text in (architect, coder, critic):
            self.assertIn('required_reading_bundle', text)
            self.assertIn('follow `not_declared` in that rule', text)  # no bundle: point to the one home

    def test_no_list_fallback_is_one_line_and_defined_once(self):
        default = ROOT / 'bSmart_Templates' / 'required-reading-default.md'
        text = read(default)
        self.assertIn('No custom required-reading list is defined for this project', text)
        self.assertIn('## Required reading bundle', text)
        self.assertIn('required_reading_bundle:', text)
        self.assertLess(len(text.split()), 120)  # stays very brief
        note = 'No required reading defined: bSmart-System/bSmart_Templates/required-reading-default.md'
        files = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.md', '.yaml'}
                 and '.git' not in p.parts and p.name != 'bSmart_Version.md']
        hits = sorted(p.relative_to(ROOT).as_posix() for p in files if note in read(p))
        self.assertEqual(hits, ['bSmart_Protocols/projects.md'])
        projects = read(ROOT / 'bSmart_Protocols' / 'projects.md')
        self.assertIn('once per task, in the task report, not at every step', projects)
        self.assertIn('required_reading_default:', projects)
        self.assertIn('required-reading-default.md', read(ROOT / 'bSmart_Map.md'))
        # The old silent skip is gone everywhere.
        for p in files:
            body = read(p)
            for old in ['Skip silently and continue', 'skip this silently', 'skip this check silently',
                        'skip it silently']:
                self.assertNotIn(old, body, p)

    def test_new_project_templates_have_empty_bundle(self):
        project = (ROOT / 'bSmart_Templates' / 'project.template.md').read_text(encoding='utf-8')
        self.assertIn('required_reading_bundle: []', project)

    def test_hold_is_blocking_and_defined_once(self):
        critic = read(EXT / 'bCritic' / 'critic.md')
        self.assertIn('## HOLD', critic)
        self.assertIn('one exception to the rule that a review never blocks the work', critic)
        self.assertIn('cannot pass at any score', critic)
        self.assertIn('The only exception is a HOLD', critic)
        self.assertNotIn('caps the score', critic)
        files = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.md', '.yaml'}
                 and '.git' not in p.parts]
        for phrase in ['## HOLD', 'cannot pass at any score', 'caps the score at 7']:
            hits = sorted(p.relative_to(ROOT).as_posix() for p in files if phrase in read(p))
            expected = [] if phrase == 'caps the score at 7' else ['bSmart-Extensions/bCritic/critic.md']
            self.assertEqual(hits, expected, phrase)
        self.assertIn('HOLD:', read(EXT / 'bCritic' / 'templates' / 'critique.template.md'))
        self.assertIn('HOLD (bCritic) blocks acceptance', read(BSWARM / 'bswarm-protocol.md'))

    def test_acknowledgement_shape_has_one_home(self):
        files = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.md', '.yaml', '.py'}
                 and '.git' not in p.parts and p.name != 'test_required_reading.py']
        for key in ['not_applicable_with_reason:', 'revision_or_sha256:', 'critic_compliance:']:
            hits = sorted(p.relative_to(ROOT).as_posix() for p in files
                          if key in p.read_text(encoding='utf-8', errors='ignore'))
            self.assertEqual(hits, ['bSmart-Extensions/bArchitect/architect.md'], key)
        architect = (EXT / 'bArchitect' / 'architect.md').read_text(encoding='utf-8')
        for key in SHAPE_KEYS:
            self.assertIn(key, architect)

    def test_bswarm_preflight_and_outputs(self):
        protocol = read(BSWARM / 'bswarm-protocol.md')
        self.assertIn('### Required reading check', protocol)
        self.assertIn('does not change permissions, models, or round limits', protocol)
        self.assertRegex(protocol, r'required_reading: not_declared \| acknowledged')
        spec = (BSWARM / 'templates' / 'run-spec.yaml').read_text(encoding='utf-8')
        self.assertTrue(re.search(r'(?m)^\s+required_reading:\n\s+#', spec))
        self.assertIn('## Required reading', read(BSWARM / 'templates' / 'jobs' / 'report.template.md'))
        self.assertIn('## Required reading', read(BSWARM / 'templates' / 'jobs' / 'plan.template.md'))
        self.assertIn('required reading', read(BSWARM / 'templates' / 'jobs' / 'SPEC.md'))


if __name__ == '__main__':
    unittest.main()
