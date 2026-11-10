import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXT = ROOT / 'bSmart-Extensions'
BSWARM = EXT / 'bSwarm'
DONE = 'no knowledge changes needed'
SKILLS = {'bCoder': 'coder.md', 'bArchitect': 'architect.md', 'bCritic': 'critic.md'}


def read(path):
    # Collapse whitespace so wrapped Markdown lines still match.
    return ' '.join(path.read_text(encoding='utf-8').split())


class KnowledgeUpkeepTests(unittest.TestCase):
    def test_core_manifest_has_knowledge_upkeep_rule(self):
        core = read(ROOT / 'bSmart.md')
        for term in ['knowledge_upkeep:', 'modifies, fixes, or refactors code',
                     'update or remove', DONE, '`Code:` line']:
            self.assertIn(term, core)

    def test_knowledge_protocol_and_template_define_code_line(self):
        protocol = read(ROOT / 'bSmart_Protocols' / 'knowledge.md')
        self.assertIn('## Code references and upkeep', protocol)
        self.assertIn('- Code: `', protocol)
        self.assertIn('knowledge_upkeep', protocol)
        template = read(ROOT / 'bSmart_Templates' / 'project-knowledge.README.template.md')
        self.assertIn('`Code:` line', template)

    def test_role_skills_exist_and_are_registered(self):
        core = read(ROOT / 'bSmart.md')
        features = read(ROOT / 'bSmart_Features.md')
        docs = read(ROOT / 'bSmart_Docs' / 'extensions.md')
        for name, rules in SKILLS.items():
            self.assertTrue((EXT / name / 'README.md').exists(), name)
            self.assertTrue((EXT / name / rules).exists(), name)
            self.assertIn(f'{name}:', core)
            self.assertIn(f'### {name}', features)
            self.assertIn(name, docs)

    def test_role_skills_carry_the_knowledge_steps(self):
        coder = read(EXT / 'bCoder' / 'coder.md')
        for term in ['Search the knowledge for anything relevant to your task',
                     'Update the knowledge before handing in your work',
                     'knowledge_upkeep', DONE]:
            self.assertIn(term, coder)
        architect = read(EXT / 'bArchitect' / 'architect.md')
        for term in ['relevant_knowledge', 'final knowledge check across the whole change', DONE]:
            self.assertIn(term, architect)
        critic = read(EXT / 'bCritic' / 'critic.md')
        for term in ['knowledge was read and kept in step with the code',
                     'flag knowledge that is stale or missing']:
            self.assertIn(term, critic)

    def test_bswarm_uses_the_skills_and_records_knowledge(self):
        protocol = read(BSWARM / 'bswarm-protocol.md')
        for term in ['The architect follows bArchitect', 'The coder follows bCoder',
                     'Both critics follow bCritic', "bArchitect's final knowledge check",
                     'knowledge_changes:', DONE, '## 13. Project tracking', 'handoff.md', 'decisions.md']:
            self.assertIn(term, protocol)
        readme = read(BSWARM / 'README.md')
        for name in SKILLS:
            self.assertIn(name, readme)
        self.assertIn('Final knowledge check', read(BSWARM / 'templates' / 'run-record.md'))
        self.assertIn('## Knowledge changes', read(BSWARM / 'templates' / 'jobs' / 'report.template.md'))
        self.assertIn('knowledge changes', read(BSWARM / 'templates' / 'jobs' / 'SPEC.md'))

    def test_backlog_setting_renamed_and_old_name_still_accepted(self):
        # No script reads this project.md field; agents follow the docs, so the
        # docs must name the new field and keep accepting the old one.
        projects = read(ROOT / 'bSmart_Protocols' / 'projects.md')
        self.assertIn('deferred_issues: project | workstream', projects)
        self.assertIn('Old name bswarm_deferred_issues is still accepted', projects)
        critic = read(EXT / 'bCritic' / 'critic.md')
        self.assertIn('`deferred_issues: project | workstream`', critic)
        self.assertIn('The old name `bswarm_deferred_issues` still works', critic)
        self.assertIn('`deferred_issues` wins', critic)
        bmap = read(EXT / 'bMap' / 'bmap-protocol.md')
        self.assertIn('use the value of `deferred_issues`, then the old name `bswarm_deferred_issues`', bmap)
        # Outside the alias notes, the old name is not used as the setting.
        for path in [ROOT / 'bSmart_Map.md', BSWARM / 'bswarm-protocol.md', ROOT / 'bSmart_Features.md']:
            text = read(path)
            self.assertNotIn('`bswarm_deferred_issues: workstream`', text, path)

    def test_role_skills_in_numbered_feature_list(self):
        features = (ROOT / 'bSmart_Features.md').read_text(encoding='utf-8')
        for line in ['20. bCoder — ', '21. bArchitect — ', '22. bCritic — ', '20. bCoder\n',
                     '- name: bCritic\n']:
            self.assertIn(line, features)

    def test_role_rules_have_one_home(self):
        # Key role rules live only in the skill files, never again in bSwarm.
        homes = {
            'stop at 8 or higher': 'bCritic',
            'IDs are stable': 'bCritic',
            '### C<id> [<severity>] [<class>] [<status>]': 'bCritic',
            'Nit, hygiene, taste': 'bCritic',
            'target_words: 350-500': 'bArchitect',
            'Update the knowledge before handing in': 'bCoder',
        }
        files = [p for p in EXT.rglob('*') if p.is_file() and p.suffix in {'.md', '.yaml'}]
        for phrase, home in homes.items():
            hits = sorted({p.relative_to(EXT).parts[0] for p in files if phrase in read(p)})
            self.assertEqual(hits, [home], phrase)


if __name__ == '__main__':
    unittest.main()
