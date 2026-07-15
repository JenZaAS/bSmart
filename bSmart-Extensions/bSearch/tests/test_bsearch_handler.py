import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

FIXTURE_ROOT = Path('/workspace/bSmart-Extensions/bSearch')
MODULE_PATH = FIXTURE_ROOT / 'bsearch_handler.py'


def load_handler_module():
    spec = importlib.util.spec_from_file_location('bsearch_handler', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BSearchHandlerTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name) / 'bsearch'
        shutil.copytree(FIXTURE_ROOT, self.root)
        for path in self.root.rglob('__pycache__'):
            shutil.rmtree(path, ignore_errors=True)
        self.module = load_handler_module()
        self.handler = self.module.BSearchHandler(self.root)

    def tearDown(self):
        self.tmpdir.cleanup()

    def read_jsonl(self, relative_path):
        path = self.root / relative_path
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

    def clear_manual_run_history(self):
        for relative_path in ['runs/candidate-pool-history.jsonl', 'runs/delivered-history.jsonl']:
            path = self.root / relative_path
            rows = [row for row in self.read_jsonl(relative_path) if row.get('run_type') != 'manual_run']
            path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')

    def fake_github_api_json(self, url):
        if '/repos/' in url:
            if url.endswith('/Graphify-Labs/graphify'):
                return {
                    'name': 'graphify',
                    'description': 'Knowledge graph platform for code and docs',
                    'topics': ['knowledge-graph', 'graphrag'],
                    'html_url': 'https://github.com/Graphify-Labs/graphify',
                    'homepage': 'https://www.graphify.com',
                }
            raise AssertionError(f'unexpected repo url: {url}')
        parsed = urlparse(url)
        query = parse_qs(parsed.query).get('q', [''])[0]
        repo_name = query.lower().replace(' ', '-')[:20] or 'demo-repo'
        return {
            'items': [
                {
                    'name': repo_name,
                    'description': f'{query} toolkit for automation',
                    'topics': ['agent', 'automation'] if 'agent' in query.lower() else ['matlab'] if 'matlab' in query.lower() else ['knowledge-graph'] if 'graph' in query.lower() else ['docker'],
                    'html_url': f'https://github.com/example/{repo_name}',
                    'homepage': '',
                    'stargazers_count': 1000,
                }
            ]
        }

    def fake_fetch_rss_items(self, url):
        if 'news.google.com' in url:
            query = parse_qs(urlparse(url).query).get('q', ['news'])[0]
            return [
                {
                    'title': f'{query} article',
                    'link': f'https://example.com/{query.replace(" ", "-")}',
                    'description': f'{query} blog coverage for automation and tooling',
                }
            ]
        if 'export.arxiv.org' in url:
            return [
                {
                    'title': 'GraphRAG for agent memory',
                    'link': 'https://arxiv.org/abs/1234.5678',
                    'description': 'Research paper about graph memory and agent tooling',
                }
            ]
        raise AssertionError(f'unexpected rss url: {url}')

    def fake_fetch_youtube_search_items(self, query):
        return [
            {
                'title': f'{query} video',
                'link': f'https://www.youtube.com/watch?v={query.lower().replace(" ", "")[:10]}',
                'description': f'{query} walkthrough for automation and tooling',
            }
        ]

    def test_insert_github_url_updates_histories_and_profile(self):
        self.handler._github_api_json = self.fake_github_api_json
        result = self.handler.handle('bSearch insert https://github.com/Graphify-Labs/graphify 5')
        self.assertEqual(result['command_family'], 'insert')
        self.assertEqual(result['item']['title'].lower(), 'graphify')
        self.assertEqual(result['item']['user_feedback_score'], 5)

        feedback = self.read_jsonl('data/feedback-history.jsonl')
        self.assertEqual(feedback[-1]['title'].lower(), 'graphify')
        self.assertTrue(feedback[-1]['manual_inserted'])

        delivered = self.read_jsonl('runs/delivered-history.jsonl')
        self.assertEqual(delivered[-1]['title'].lower(), 'graphify')

        profile = (self.root / 'user-interest-profile.md').read_text(encoding='utf-8')
        self.assertIn('Code knowledge graph', profile)

    def test_list_default_returns_categories_sorted_by_score(self):
        result = self.handler.handle('bSearch list')
        self.assertEqual(result['command_family'], 'list')
        self.assertEqual(result['view'], 'categories')
        self.assertEqual(result['sort'], 'score')
        self.assertLessEqual(len(result['entries']), 10)
        scores = [entry['score'] for entry in result['entries']]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_list_category_with_limit_returns_items(self):
        self.handler._github_api_json = self.fake_github_api_json
        self.handler.handle('bSearch insert https://github.com/Graphify-Labs/graphify 5')
        result = self.handler.handle('bSearch list Code knowledge graph 4')
        self.assertEqual(result['view'], 'category_items')
        self.assertEqual(result['resolved_category'], 'Code knowledge graph')
        self.assertLessEqual(len(result['entries']), 4)
        self.assertEqual(result['entries'][0]['title'].lower(), 'graphify')

    def test_rate_appends_feedback_and_refreshes_category_stats(self):
        result = self.handler.handle('bSearch rate OpenHands 5')
        self.assertEqual(result['command_family'], 'rate')
        feedback = self.read_jsonl('data/feedback-history.jsonl')
        self.assertEqual(feedback[-1]['title'], 'OpenHands')
        self.assertEqual(feedback[-1]['user_feedback_score'], 5)
        stats = json.loads((self.root / 'data/category-stats.json').read_text(encoding='utf-8'))
        self.assertEqual(stats['Autonomous coding agent']['feedback_max'], 5)

    def test_show_returns_item_details(self):
        result = self.handler.handle('bSearch show Graphiti')
        self.assertEqual(result['command_family'], 'show')
        self.assertEqual(result['item']['title'], 'Graphiti')
        self.assertIn('links', result['item'])
        self.assertTrue(result['item']['links'])

    def test_search_memory_finds_matching_items(self):
        result = self.handler.handle('bSearch search memory MATLAB')
        self.assertEqual(result['command_family'], 'search_memory')
        titles = [entry['title'] for entry in result['entries']]
        self.assertIn('matlab-actions', titles)

    def test_set_updates_config(self):
        result = self.handler.handle('bSearch set exploration 0.3')
        self.assertEqual(result['command_family'], 'settings')
        config_text = (self.root / 'config.yaml').read_text(encoding='utf-8')
        self.assertIn('exploration_strength: 0.3', config_text)

    def test_remove_archives_item_from_default_browsing(self):
        result = self.handler.handle('bSearch remove Factorio')
        self.assertEqual(result['command_family'], 'remove')
        listed = self.handler.handle('bSearch list Systems game all')
        titles = [entry['title'] for entry in listed['entries']]
        self.assertNotIn('Factorio', titles)

    def test_run_creates_new_run_artifacts(self):
        self.clear_manual_run_history()
        self.handler._github_api_json = self.fake_github_api_json
        self.handler._fetch_rss_items = self.fake_fetch_rss_items
        self.handler._fetch_youtube_search_items = self.fake_fetch_youtube_search_items
        result = self.handler.handle('bSearch run')
        self.assertEqual(result['command_family'], 'run')
        self.assertEqual(result['discovery_mode'], 'multisource_live_discovery')
        self.assertEqual(result['source_strategy'], 'random_source_per_slot')
        self.assertIn('GitHub project', result['source_types'])
        self.assertIn('News/Blog post', result['source_types'])
        self.assertIn('Research paper', result['source_types'])
        self.assertIn('YouTube video', result['source_types'])
        self.assertTrue(result['candidate_titles'])
        self.assertTrue(result['run_timestamp_utc'])
        state_text = (self.root / 'state.yaml').read_text(encoding='utf-8')
        self.assertIn(result['run_timestamp_utc'], state_text)
        run_file = self.root / 'runs' / f"{result['run_timestamp_utc'][:10]}_run.md"
        self.assertTrue(run_file.exists())
        candidates = self.read_jsonl('runs/candidate-pool-history.jsonl')
        self.assertTrue(any(row.get('run_type') == 'manual_run' for row in candidates))

    def test_run_is_blocked_when_previous_run_is_unhandled(self):
        self.clear_manual_run_history()
        self.handler._github_api_json = self.fake_github_api_json
        self.handler._fetch_rss_items = self.fake_fetch_rss_items
        self.handler._fetch_youtube_search_items = self.fake_fetch_youtube_search_items
        first = self.handler.handle('bSearch run')
        self.assertEqual(first['command_family'], 'run')
        second = self.handler.handle('bSearch run')
        self.assertEqual(second['command_family'], 'run')
        self.assertEqual(second['status'], 'blocked_unhandled_previous_run')
        self.assertEqual(second['review_command'], 'bSearch review pending')
        self.assertGreater(second['pending_count'], 0)

    def test_review_pending_returns_latest_unhandled_items(self):
        self.clear_manual_run_history()
        self.handler._github_api_json = self.fake_github_api_json
        self.handler._fetch_rss_items = self.fake_fetch_rss_items
        self.handler._fetch_youtube_search_items = self.fake_fetch_youtube_search_items
        self.handler.handle('bSearch run')
        result = self.handler.handle('bSearch review pending')
        self.assertEqual(result['command_family'], 'review_pending')
        self.assertEqual(result['status'], 'pending_run_ready_for_review')
        self.assertGreater(result['pending_count'], 0)
        self.assertTrue(result['entries'])


if __name__ == '__main__':
    unittest.main()
