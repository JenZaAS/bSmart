from __future__ import annotations

import json
import random
import re
import html
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class BSearchHandler:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.context_file = self.root / 'data' / 'command-context.json'
        self.status_file = self.root / 'data' / 'item-status.jsonl'

    def handle(self, command: str) -> Dict[str, Any]:
        command = command.strip()
        if not command.startswith('bSearch'):
            raise ValueError('Command must begin with bSearch')
        remainder = command[len('bSearch'):].strip()
        lowered = remainder.lower()

        if lowered.startswith(('insert ', 'add ')):
            return self._handle_insert(command, remainder)
        if lowered.startswith(('rate ', 'score ', 'update score')):
            return self._handle_rate(command, remainder)
        if lowered.startswith(('show profile', 'update profile', 'add interest', 'remove interest')):
            return self._handle_profile(command, remainder)
        if lowered.startswith(('review pending', 'pending review', 'review latest', 'pending')):
            return self._handle_review_pending(command, remainder)
        if lowered.startswith(('show ', 'open ', 'tell me about ')):
            return self._handle_show(command, remainder)
        if lowered.startswith(('search memory', 'find saved')):
            return self._handle_search_memory(command, remainder)
        if lowered.startswith(('settings', 'set ')):
            return self._handle_settings(command, remainder)
        if lowered.startswith(('remove ', 'archive ')):
            return self._handle_remove(command, remainder)
        if lowered in ('run', 'search now') or lowered.startswith('run ') or lowered.startswith('search now '):
            return self._handle_run(command, remainder)
        if lowered.startswith('list'):
            return self._handle_list(command, remainder)
        raise ValueError(f'Unsupported bSearch command: {command}')

    def _now_utc(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

    def _read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

    def _append_jsonl(self, path: Path, record: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')

    def _load_config_text(self) -> str:
        return (self.root / 'config.yaml').read_text(encoding='utf-8')

    def _save_config_text(self, text: str) -> None:
        (self.root / 'config.yaml').write_text(text, encoding='utf-8')

    def _load_state_text(self) -> str:
        return (self.root / 'state.yaml').read_text(encoding='utf-8')

    def _save_state_text(self, text: str) -> None:
        (self.root / 'state.yaml').write_text(text, encoding='utf-8')

    def _load_context(self) -> Dict[str, Any]:
        if not self.context_file.exists():
            return {}
        return json.loads(self.context_file.read_text(encoding='utf-8'))

    def _save_context(self, context: Dict[str, Any]) -> None:
        self.context_file.write_text(json.dumps(context, indent=2) + '\n', encoding='utf-8')

    def _load_archived_titles(self) -> set[str]:
        archived = set()
        for row in self._read_jsonl(self.status_file):
            if row.get('status') == 'archived':
                archived.add(row['title'].lower())
            elif row.get('status') == 'active' and row['title'].lower() in archived:
                archived.remove(row['title'].lower())
        return archived

    def _extract_config(self) -> Dict[str, Any]:
        text = self._load_config_text()

        def capture(pattern: str, cast=str, default=None):
            m = re.search(pattern, text, flags=re.MULTILINE)
            if not m:
                return default
            return cast(m.group(1))

        preferred = re.findall(r'^\s+-\s+(.+)$', text.split('preferred:')[1].split('emphasized_topics:')[0], flags=re.MULTILINE) if 'preferred:' in text and 'emphasized_topics:' in text else []
        topics = re.findall(r'^\s+-\s+(.+)$', text.split('emphasized_topics:')[1], flags=re.MULTILINE) if 'emphasized_topics:' in text else []
        return {
            'timezone': capture(r'^\s*timezone:\s*(.+)$', str, 'UTC'),
            'candidate_pool_size': capture(r'^\s*candidate_pool_size:\s*(\d+)$', int, 10),
            'delivered_item_count': capture(r'^\s*delivered_item_count:\s*(\d+)$', int, 5),
            'exploration_strength': capture(r'^\s*exploration_strength:\s*([0-9.]+)$', float, 0.5),
            'preferred_provider': capture(r'^\s*preferred_provider:\s*(.+)$', str, 'openai-codex'),
            'preferred_model': capture(r'^\s*preferred_model:\s*(.+)$', str, 'gpt-5.4'),
            'preferred_sources': preferred,
            'emphasized_topics': topics,
        }

    def _all_candidate_rows(self) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.root / 'runs' / 'candidate-pool-history.jsonl')

    def _all_feedback_rows(self) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.root / 'data' / 'feedback-history.jsonl')

    def _all_delivered_rows(self) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.root / 'runs' / 'delivered-history.jsonl')

    def _latest_run_markdown_titles(self, run_timestamp_utc: str) -> List[str]:
        run_file = self.root / 'runs' / f"{run_timestamp_utc[:10]}_run.md"
        if not run_file.exists():
            return []
        text = run_file.read_text(encoding='utf-8')
        titles = re.findall(r'^###\s+\d+\.\s+(.+)$', text, flags=re.MULTILINE)
        if titles:
            return [title.strip() for title in titles]
        shortlist = []
        in_shortlist = False
        for line in text.splitlines():
            if line.strip() == '## Shortlist':
                in_shortlist = True
                continue
            if in_shortlist and line.startswith('## '):
                break
            m = re.match(r'^\d+\.\s+\*\*(.+?)\*\*', line.strip())
            if m:
                shortlist.append(m.group(1).strip())
        return shortlist

    def _latest_unhandled_run(self) -> Optional[Dict[str, Any]]:
        delivered_rows = [row for row in self._all_delivered_rows() if row.get('run_type') == 'manual_run']
        if not delivered_rows:
            return None
        latest_timestamp = max(row['run_timestamp_utc'] for row in delivered_rows if row.get('run_timestamp_utc'))
        latest_titles = self._latest_run_markdown_titles(latest_timestamp)
        if not latest_titles:
            latest_titles = [row.get('title', '') for row in delivered_rows if row.get('run_timestamp_utc') == latest_timestamp]
        latest_titles = [title for title in latest_titles if title]
        feedback_rows = self._all_feedback_rows()
        status_rows = self._read_jsonl(self.status_file)
        pending_titles = []
        for title in latest_titles:
            title_key = title.lower()
            handled_by_feedback = any(
                fb.get('title', '').lower() == title_key and (fb.get('recorded_at_utc') or fb.get('run_timestamp_utc', '')) > latest_timestamp
                for fb in feedback_rows
            )
            handled_by_status = any(
                status.get('title', '').lower() == title_key and (status.get('recorded_at_utc') or '') > latest_timestamp
                for status in status_rows
            )
            if not handled_by_feedback and not handled_by_status:
                pending_titles.append(title)
        if not pending_titles:
            return None
        return {
            'run_timestamp_utc': latest_timestamp,
            'pending_titles': pending_titles,
            'pending_count': len(pending_titles),
            'total_count': len(latest_titles),
        }

    def _current_items(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        candidates = self._all_candidate_rows()
        feedback_rows = self._all_feedback_rows()
        delivered_rows = self._all_delivered_rows()
        archived = self._load_archived_titles()

        latest_candidate: Dict[str, Dict[str, Any]] = {}
        for row in candidates:
            latest_candidate[row['title'].lower()] = row

        latest_delivered: Dict[str, Dict[str, Any]] = {}
        for row in delivered_rows:
            latest_delivered[row['title'].lower()] = row

        latest_feedback: Dict[str, Dict[str, Any]] = {}
        for row in feedback_rows:
            latest_feedback[row['title'].lower()] = row

        titles = set(latest_candidate) | set(latest_feedback) | set(latest_delivered)
        items = []
        for key in sorted(titles):
            if not include_archived and key in archived:
                continue
            cand = latest_candidate.get(key, {})
            fb = latest_feedback.get(key, {})
            delivered = latest_delivered.get(key, {})
            title = cand.get('title') or fb.get('title') or delivered.get('title') or key
            category = fb.get('category') or cand.get('category') or delivered.get('category') or 'Uncategorized'
            links = cand.get('links', [])
            description = cand.get('description', '') or f'Stored bSearch item in category {category}.'
            score = fb.get('user_feedback_score')
            if score is None:
                score = delivered.get('final_score', cand.get('final_score', cand.get('predicted_interest', 3.0)))
            items.append({
                'title': title,
                'title_key': key,
                'category': category,
                'source_type': cand.get('source_type', delivered.get('source_type', 'Unknown')),
                'predicted_interest': float(fb.get('predicted_interest', delivered.get('predicted_interest', cand.get('predicted_interest', 3.0)))),
                'final_score': float(delivered.get('final_score', cand.get('final_score', score))),
                'score': float(score),
                'user_feedback_score': float(score),
                'links': links,
                'description': description,
                'archived': key in archived,
            })
        return items

    def _find_item(self, reference: str, include_archived: bool = False) -> Dict[str, Any]:
        reference = reference.strip()
        ref_key = reference.lower()
        items = self._current_items(include_archived=include_archived)
        for item in items:
            if item['title'].lower() == ref_key:
                return item
        matches = [item for item in items if ref_key in item['title'].lower()]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f'No stored item matched: {reference}')
        raise ValueError(f'Ambiguous item reference: {reference}')

    def _rebuild_category_stats(self) -> Dict[str, Any]:
        items = self._current_items(include_archived=False)
        grouped: Dict[str, List[float]] = defaultdict(list)
        for item in items:
            grouped[item['category']].append(float(item['score']))
        stats = {}
        for category, scores in sorted(grouped.items()):
            stats[category] = {
                'items_with_feedback': len(scores),
                'feedback_avg': round(sum(scores) / len(scores), 2),
                'feedback_min': min(scores),
                'feedback_max': max(scores),
            }
        (self.root / 'data' / 'category-stats.json').write_text(json.dumps(stats, indent=2) + '\n', encoding='utf-8')
        return stats

    def _rebuild_profile(self) -> str:
        stats = self._rebuild_category_stats()
        items = self._current_items(include_archived=False)
        strong, moderate, low = [], [], []
        for category, data in sorted(stats.items(), key=lambda kv: (-kv[1]['feedback_avg'], kv[0].lower())):
            avg = data['feedback_avg']
            if avg >= 4.5:
                strong.append((category, avg))
            elif avg >= 3.5:
                moderate.append((category, avg))
            else:
                low.append((category, avg))
        lines = [
            '# bSearch user-interest profile',
            '',
            'Status: Feedback-informed',
            f'Updated: {self._now_utc()[:10]}',
            '',
            '## Strong current signals',
        ]
        if strong:
            for category, avg in strong:
                lines.append(f'- {category} — current feedback average `{avg}`')
        else:
            lines.append('- No strong signal yet.')
        lines += ['', '## Moderate current signals']
        if moderate:
            for category, avg in moderate:
                lines.append(f'- {category} — current feedback average `{avg}`')
        else:
            lines.append('- No moderate signal yet.')
        lines += ['', '## Lower-interest signals from this round']
        if low:
            for category, avg in low:
                lines.append(f'- {category} — current feedback average `{avg}`')
        else:
            lines.append('- No lower-interest signal yet.')
        lines += ['', '## Discovery preference']
        lines += [
            '- Keep some controlled surprise and novelty rather than collapsing into a narrow loop.',
            '- Prefer actionable technical discoveries over hype-driven content.',
        ]
        if strong:
            lines.append(f"- Current strongest areas: {', '.join(category for category, _ in strong)}.")
        lines += ['', '## Saved items overview']
        for item in sorted(items, key=lambda x: (-x['score'], x['title'].lower()))[:12]:
            lines.append(f"- {item['title']}: `{item['score']}`")
        content = '\n'.join(lines) + '\n'
        (self.root / 'user-interest-profile.md').write_text(content, encoding='utf-8')
        return content

    def _parse_score_and_reference(self, text: str) -> tuple[str, float]:
        m = re.search(r'(.+?)\s+([1-5](?:\.\d+)?)\s*$', text.strip())
        if not m:
            raise ValueError('A score from 1 to 5 is required at the end of the command.')
        ref = m.group(1).strip()
        score = float(m.group(2))
        if not (1 <= score <= 5):
            raise ValueError('Score must be between 1 and 5.')
        return ref, score

    def _http_text(self, url: str) -> str:
        req = urllib.request.Request(url, headers={'User-Agent': 'SschwAdmin-bSearch'})
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8', errors='replace')

    def _github_api_json(self, url: str) -> Dict[str, Any]:
        return json.loads(self._http_text(url))

    def _fetch_rss_items(self, url: str) -> List[Dict[str, str]]:
        text = self._http_text(url)
        root = ET.fromstring(text)
        items = []
        for item in root.findall('.//item')[:12]:
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            description = (item.findtext('description') or item.findtext('{http://www.w3.org/2005/Atom}summary') or '').strip()
            if title and link:
                items.append({'title': title, 'link': link, 'description': description})
        if not items:
            ns = {'a': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('.//a:entry', ns)[:12]:
                title = (entry.findtext('a:title', default='', namespaces=ns) or '').strip()
                link_node = entry.find('a:link', ns)
                link = (link_node.attrib.get('href') if link_node is not None else '').strip()
                description = (entry.findtext('a:summary', default='', namespaces=ns) or '').strip()
                if title and link:
                    items.append({'title': title, 'link': link, 'description': description})
        return items

    def _fetch_arxiv_items(self, query: str) -> List[Dict[str, str]]:
        url = 'https://export.arxiv.org/api/query?' + urllib.parse.urlencode({
            'search_query': f'all:{query}',
            'start': 0,
            'max_results': 5,
        })
        return self._fetch_rss_items(url)

    def _fetch_youtube_search_items(self, query: str) -> List[Dict[str, str]]:
        rss_url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({
            'q': f'{query} site:youtube.com/watch',
            'hl': 'en-US',
            'gl': 'US',
            'ceid': 'US:en',
        })
        items = []
        for entry in self._fetch_rss_items(rss_url)[:8]:
            title = html.unescape(entry.get('title', '')).strip()
            description = re.sub(r'<[^>]+>', '', entry.get('description', '')).strip()
            link = entry.get('link', '').strip()
            if not title or not link:
                continue
            items.append({'title': title, 'link': link, 'description': description})
        return items

    def _resolve_item_reference(self, reference: str, score: float) -> Dict[str, Any]:
        github_match = re.match(r'https?://github\.com/([^/]+)/([^/#?]+)', reference)
        if github_match:
            owner, repo = github_match.groups()
            data = self._github_api_json(f'https://api.github.com/repos/{owner}/{repo}')
            title = data.get('name') or repo
            topics = [t.lower() for t in data.get('topics', [])]
            category = 'GitHub project'
            if 'knowledge-graph' in topics or 'graphrag' in topics:
                category = 'Code knowledge graph'
            elif 'matlab' in title.lower() or 'matlab' in (data.get('description') or '').lower():
                category = 'MATLAB tooling'
            elif 'agent' in topics or 'codex' in topics or 'claude-code' in topics:
                category = 'Autonomous coding agent'
            description = data.get('description') or f'GitHub project {owner}/{repo}'
            links = [data.get('html_url')]
            if data.get('homepage'):
                links.append(data['homepage'])
            return {
                'title': title,
                'category': category,
                'source_type': 'GitHub project',
                'predicted_interest': round(max(3.0, min(5.0, score - 0.05)), 2),
                'final_score': round(max(3.0, min(5.0, score - 0.05)), 2),
                'links': [link for link in links if link],
                'description': description,
                'source_reference': reference,
            }
        huggingface_match = re.match(r'https?://huggingface\.co/([^/]+)/([^/#?]+)', reference)
        if huggingface_match:
            owner, model = huggingface_match.groups()
            return {
                'title': model,
                'category': 'Local LLM / model runtime',
                'source_type': 'Hugging Face model',
                'predicted_interest': round(max(3.0, min(5.0, score - 0.05)), 2),
                'final_score': round(max(3.0, min(5.0, score - 0.05)), 2),
                'links': [reference],
                'description': f'Hugging Face GGUF model {owner}/{model}; candidate input for local large-model runtime discussions.',
                'source_reference': reference,
            }

        youtube_match = re.match(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})', reference)
        if youtube_match:
            video_id = youtube_match.group(1)
            return {
                'title': f'YouTube video {video_id}',
                'category': 'Local LLM / model runtime',
                'source_type': 'YouTube video',
                'predicted_interest': round(max(3.0, min(5.0, score - 0.05)), 2),
                'final_score': round(max(3.0, min(5.0, score - 0.05)), 2),
                'links': [reference],
                'description': 'YouTube video input for local large-model/runtime discussion.',
                'source_reference': reference,
            }

        try:
            known = self._find_item(reference, include_archived=True)
            return {
                'title': known['title'],
                'category': known['category'],
                'source_type': known['source_type'],
                'predicted_interest': known['predicted_interest'],
                'final_score': known['final_score'],
                'links': known['links'],
                'description': known['description'],
                'source_reference': reference,
            }
        except Exception:
            pass
        query = urllib.parse.quote(reference)
        search = self._github_api_json(f'https://api.github.com/search/repositories?q={query}&per_page=1')
        items = search.get('items') or []
        if items:
            return self._resolve_item_reference(items[0]['html_url'], score)
        raise ValueError(f'Could not resolve item reference: {reference}')

    def _append_candidate_record(self, *, now: str, run_type: str, item: Dict[str, Any], command: Optional[str] = None) -> None:
        candidate_record = {
            'run_timestamp_utc': now,
            'run_type': run_type,
            'candidate_position': item.get('candidate_position', 1),
            'candidate_pool_size': item.get('candidate_pool_size', 1),
            'title': item['title'],
            'source_type': item['source_type'],
            'category': item['category'],
            'predicted_interest': item['predicted_interest'],
            'rank_progress': item.get('rank_progress', 1.0),
            'final_score': item['final_score'],
            'links': item.get('links', []),
            'description': item.get('description', ''),
            'manual_inserted': run_type == 'manual_insert',
        }
        if command:
            candidate_record['manual_insert_input'] = command
        self._append_jsonl(self.root / 'runs' / 'candidate-pool-history.jsonl', candidate_record)

    def _append_delivered_record(self, *, now: str, run_type: str, item: Dict[str, Any]) -> None:
        delivered_record = {
            'run_timestamp_utc': now,
            'run_type': run_type,
            'title': item['title'],
            'category': item['category'],
            'predicted_interest': item['predicted_interest'],
            'final_score': item['final_score'],
            'source_type': item['source_type'],
            'manual_inserted': run_type == 'manual_insert',
        }
        self._append_jsonl(self.root / 'runs' / 'delivered-history.jsonl', delivered_record)

    def _record_candidate_delivery_feedback(self, *, now: str, run_type: str, item: Dict[str, Any], score: Optional[float], command: Optional[str] = None, comment: str = '', delivered_to_user: bool = True) -> None:
        candidate_record = {
            'run_timestamp_utc': now,
            'run_type': run_type,
            'candidate_position': item.get('candidate_position', 1),
            'candidate_pool_size': item.get('candidate_pool_size', 1),
            'title': item['title'],
            'source_type': item['source_type'],
            'category': item['category'],
            'predicted_interest': item['predicted_interest'],
            'rank_progress': item.get('rank_progress', 1.0),
            'final_score': item['final_score'],
            'links': item.get('links', []),
            'description': item.get('description', ''),
            'manual_inserted': run_type == 'manual_insert',
        }
        if command:
            candidate_record['manual_insert_input'] = command
        delivered_record = {
            'run_timestamp_utc': now,
            'run_type': run_type,
            'title': item['title'],
            'category': item['category'],
            'predicted_interest': item['predicted_interest'],
            'final_score': item['final_score'],
            'source_type': item['source_type'],
            'manual_inserted': run_type == 'manual_insert',
        }
        self._append_jsonl(self.root / 'runs' / 'candidate-pool-history.jsonl', candidate_record)
        if delivered_to_user:
            self._append_jsonl(self.root / 'runs' / 'delivered-history.jsonl', delivered_record)
        if score is not None:
            feedback_record = {
                'run_timestamp_utc': now,
                'run_type': run_type,
                'title': item['title'],
                'category': item['category'],
                'predicted_interest': item['predicted_interest'],
                'final_score': item['final_score'],
                'user_feedback_score': score,
                'user_feedback_comment': comment,
                'recorded_at_utc': now,
                'manual_inserted': run_type == 'manual_insert',
                'source_reference': (item.get('source_reference') or (item.get('links') or [''])[0] or item['title']),
            }
            self._append_jsonl(self.root / 'data' / 'feedback-history.jsonl', feedback_record)

    def _classify_github_repo(self, repo: Dict[str, Any]) -> str:
        title = (repo.get('name') or '').lower()
        description = (repo.get('description') or '').lower()
        topics = [t.lower() for t in repo.get('topics') or []]
        text = ' '.join([title, description, ' '.join(topics)])
        if any(term in text for term in ['knowledge-graph', 'graphrag', 'graphify', 'graphiti']):
            return 'Code knowledge graph'
        if 'matlab' in text:
            return 'MATLAB CI/CD' if any(term in text for term in ['action', 'ci', 'workflow', 'github-actions']) else 'MATLAB tooling'
        if any(term in text for term in ['agent', 'autonomous', 'copilot', 'claude', 'codex']):
            return 'Autonomous coding agent'
        if any(term in text for term in ['docker', 'container', 'deployment', 'devops', 'kubernetes']):
            return 'DevOps tool'
        if any(term in text for term in ['game', 'unity', 'godot', 'unreal', 'mod']):
            return 'Computer game tooling'
        return 'GitHub project'

    def _classify_text_item(self, text: str, source_type: str) -> str:
        lower = text.lower()
        if any(term in lower for term in ['knowledge graph', 'graphrag', 'graph memory', 'graphiti', 'graphify']):
            return 'Code knowledge graph'
        if 'matlab' in lower:
            return 'MATLAB tooling'
        if any(term in lower for term in ['agent', 'automation', 'copilot', 'claude', 'codex']):
            return 'Autonomous coding agent'
        if any(term in lower for term in ['docker', 'container', 'kubernetes', 'deployment', 'dokploy']):
            return 'DevOps tool'
        if any(term in lower for term in ['game', 'unity', 'godot', 'unreal', 'simulation']):
            return 'Computer game tooling'
        if source_type == 'Research paper':
            return 'Research paper'
        return 'Technical article'

    def _predict_interest_from_text(self, text: str, config: Dict[str, Any], source_type: str) -> float:
        lower = text.lower()
        score = 2.7
        if 'matlab' in lower:
            score += 1.15
        if any(term in lower for term in ['agent', 'automation', 'hermes', 'tooling']):
            score += 0.85
        if any(term in lower for term in ['knowledge graph', 'graphrag', 'graph memory', 'graphiti', 'graphify']):
            score += 0.9
        if any(term in lower for term in ['docker', 'container', 'deployment', 'devops', 'dokploy']):
            score += 0.45
        if any(term in lower for term in ['game', 'simulation', 'unity', 'godot', 'unreal']):
            score += 0.3
        if source_type == 'Research paper':
            score += 0.15
        for topic in config.get('emphasized_topics', []):
            topic_lower = topic.lower()
            if 'matlab' in topic_lower and 'matlab' in lower:
                score += 0.12
            if ('agent' in topic_lower or 'hermes' in topic_lower) and any(term in lower for term in ['agent', 'automation', 'tooling']):
                score += 0.1
            if 'game' in topic_lower and 'game' in lower:
                score += 0.08
        return round(max(1.0, min(5.0, score)), 2)

    def _discover_github_candidates(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        existing_titles = {item['title'].lower() for item in self._current_items(include_archived=True)}
        archived_titles = self._load_archived_titles()
        queries = [
            'MATLAB automation',
            'MATLAB GitHub Action',
            'AI agent tooling',
            'autonomous coding agent',
            'knowledge graph for code',
            'GraphRAG',
            'docker deployment tool',
            'developer automation',
            'game systems tool',
        ]
        rng = random.Random(self._now_utc() + ':github')
        discovered: Dict[str, Dict[str, Any]] = {}
        for query in queries:
            url = 'https://api.github.com/search/repositories?' + urllib.parse.urlencode({'q': query, 'sort': 'stars', 'order': 'desc', 'per_page': 5})
            payload = self._github_api_json(url)
            for repo in payload.get('items') or []:
                title = repo.get('name') or ''
                if not title:
                    continue
                key = title.lower()
                if key in existing_titles or key in archived_titles or key in discovered:
                    continue
                text = ' '.join([title, repo.get('description') or '', ' '.join(repo.get('topics') or [])])
                discovered[key] = {
                    'title': title,
                    'source_type': 'GitHub project',
                    'category': self._classify_github_repo(repo),
                    'predicted_interest': self._predict_interest_from_text(text, config, 'GitHub project'),
                    'links': [link for link in [repo.get('html_url'), repo.get('homepage')] if link],
                    'description': repo.get('description') or f"GitHub project discovered from query '{query}'.",
                    'query': query,
                    'stars': repo.get('stargazers_count') or 0,
                    'random_factor': round(0.5 + 0.5 * rng.random(), 4),
                }
        return list(discovered.values())

    def _discover_news_candidates(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        existing_titles = {item['title'].lower() for item in self._current_items(include_archived=True)}
        archived_titles = self._load_archived_titles()
        queries = ['MATLAB automation', 'AI agent tooling', 'GraphRAG knowledge graph', 'Docker deployment']
        rng = random.Random(self._now_utc() + ':news')
        discovered: Dict[str, Dict[str, Any]] = {}
        for query in queries:
            url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': query, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})
            for entry in self._fetch_rss_items(url)[:4]:
                key = entry['title'].lower()
                if key in existing_titles or key in archived_titles or key in discovered:
                    continue
                text = f"{entry['title']} {entry.get('description', '')}"
                discovered[key] = {
                    'title': entry['title'],
                    'source_type': 'News/Blog post',
                    'category': self._classify_text_item(text, 'News/Blog post'),
                    'predicted_interest': self._predict_interest_from_text(text, config, 'News/Blog post'),
                    'links': [entry['link']],
                    'description': re.sub(r'<[^>]+>', '', entry.get('description', '')).strip() or f"Article discovered from query '{query}'.",
                    'query': query,
                    'stars': 0,
                    'random_factor': round(0.5 + 0.5 * rng.random(), 4),
                }
        return list(discovered.values())

    def _discover_arxiv_candidates(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        existing_titles = {item['title'].lower() for item in self._current_items(include_archived=True)}
        archived_titles = self._load_archived_titles()
        queries = ['agent memory', 'GraphRAG', 'MATLAB automation']
        rng = random.Random(self._now_utc() + ':arxiv')
        discovered: Dict[str, Dict[str, Any]] = {}
        for query in queries:
            for entry in self._fetch_arxiv_items(query)[:4]:
                key = entry['title'].lower()
                if key in existing_titles or key in archived_titles or key in discovered:
                    continue
                text = f"{entry['title']} {entry.get('description', '')}"
                discovered[key] = {
                    'title': entry['title'],
                    'source_type': 'Research paper',
                    'category': self._classify_text_item(text, 'Research paper'),
                    'predicted_interest': self._predict_interest_from_text(text, config, 'Research paper'),
                    'links': [entry['link']],
                    'description': re.sub(r'<[^>]+>', '', entry.get('description', '')).strip() or f"Research paper discovered from query '{query}'.",
                    'query': query,
                    'stars': 0,
                    'random_factor': round(0.5 + 0.5 * rng.random(), 4),
                }
        return list(discovered.values())

    def _discover_youtube_candidates(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        existing_titles = {item['title'].lower() for item in self._current_items(include_archived=True)}
        archived_titles = self._load_archived_titles()
        queries = ['MATLAB tutorial automation', 'AI agent tooling', 'GraphRAG code knowledge graph', 'Docker deployment walkthrough']
        rng = random.Random(self._now_utc() + ':youtube')
        discovered: Dict[str, Dict[str, Any]] = {}
        for query in queries:
            for entry in self._fetch_youtube_search_items(query)[:4]:
                key = entry['title'].lower()
                if key in existing_titles or key in archived_titles or key in discovered:
                    continue
                text = f"{entry['title']} {entry.get('description', '')}"
                discovered[key] = {
                    'title': entry['title'],
                    'source_type': 'YouTube video',
                    'category': self._classify_text_item(text, 'YouTube video'),
                    'predicted_interest': self._predict_interest_from_text(text, config, 'YouTube video'),
                    'links': [entry['link']],
                    'description': entry.get('description', '').strip() or f"YouTube video discovered from query '{query}'.",
                    'query': query,
                    'stars': 0,
                    'random_factor': round(0.5 + 0.5 * rng.random(), 4),
                }
        return list(discovered.values())

    def _discover_multisource_candidates(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        discovered: Dict[str, Dict[str, Any]] = {}
        for candidate in self._discover_github_candidates(config) + self._discover_news_candidates(config) + self._discover_arxiv_candidates(config) + self._discover_youtube_candidates(config):
            key = candidate['title'].lower()
            if key not in discovered:
                discovered[key] = candidate
        return list(discovered.values())

    def _score_discovered_candidates(self, discovered: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        ranked_seed = sorted(discovered, key=lambda x: (-x['predicted_interest'], x['source_type'], x['title'].lower()))
        total = max(len(ranked_seed), 1)
        ranked = []
        for index, item in enumerate(ranked_seed, start=1):
            rank_progress = index / total
            final_score = item['predicted_interest'] + (5 - item['predicted_interest']) * config['exploration_strength'] * rank_progress * item['random_factor']
            ranked.append(item | {
                'candidate_position': index,
                'candidate_pool_size': total,
                'rank_progress': round(rank_progress, 4),
                'final_score': round(min(5.0, final_score), 2),
            })
        ranked.sort(key=lambda x: (-x['final_score'], -x['predicted_interest'], x['source_type'], x['title'].lower()))
        return ranked

    def _select_candidates_by_random_source(self, scored: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in scored:
            buckets[item['source_type']].append(dict(item))
        for items in buckets.values():
            items.sort(key=lambda x: (-x['final_score'], -x['predicted_interest'], x['title'].lower()))
        rng = random.Random(self._now_utc() + ':source-slots')
        selected: List[Dict[str, Any]] = []
        limit = config['candidate_pool_size']
        while len(selected) < limit:
            available_sources = [source for source, items in buckets.items() if items]
            if not available_sources:
                break
            source = rng.choice(sorted(available_sources))
            selected.append(buckets[source].pop(0))
        for index, item in enumerate(selected, start=1):
            item['candidate_position'] = index
            item['candidate_pool_size'] = len(selected)
            item['rank_progress'] = round(index / max(len(selected), 1), 4)
        return selected

    def _handle_insert(self, command: str, remainder: str) -> Dict[str, Any]:
        body = re.sub(r'^(insert|add)\s+', '', remainder, flags=re.IGNORECASE)
        reference, score = self._parse_score_and_reference(body)
        resolved = self._resolve_item_reference(reference, score)
        now = self._now_utc()
        self._record_candidate_delivery_feedback(now=now, run_type='manual_insert', item=resolved, score=score, command=command, comment='manual insert')
        self._rebuild_profile()
        return {'command_family': 'insert', 'item': {'title': resolved['title'], 'category': resolved['category'], 'user_feedback_score': score, 'description': resolved['description'], 'links': resolved['links']}, 'message': f"Stored {resolved['title']} with score {score} and refreshed profile/category stats."}

    def _parse_list_tokens(self, remainder: str) -> List[str]:
        body = re.sub(r'^list\s*', '', remainder, flags=re.IGNORECASE).strip()
        return body.split() if body else []

    def _categories_from_items(self) -> List[Dict[str, Any]]:
        stats = self._rebuild_category_stats()
        return [{'category': name, 'score': float(data['feedback_avg']), 'count': data['items_with_feedback']} for name, data in stats.items()]

    def _handle_list(self, command: str, remainder: str) -> Dict[str, Any]:
        tokens = self._parse_list_tokens(remainder)
        sort_mode = 'score'
        limit: Optional[int] = 10
        show_all = False
        explicit_category_index: Optional[int] = None
        category_name_parts: List[str] = []
        ambiguous_two_numbers = False
        i = 0
        while i < len(tokens):
            token = tokens[i]
            lower = token.lower()
            if lower in ('score', 'alpha'):
                sort_mode = lower
            elif lower == 'categories':
                pass
            elif lower == 'all':
                show_all = True
                limit = None
            elif lower == 'category' and i + 1 < len(tokens):
                explicit_category_index = int(tokens[i + 1])
                i += 1
            elif lower == 'limit' and i + 1 < len(tokens):
                limit = int(tokens[i + 1])
                i += 1
            elif re.fullmatch(r'\d+', token):
                if category_name_parts or explicit_category_index is not None:
                    limit = int(token)
                elif limit == 10 and len([t for t in tokens if re.fullmatch(r'\d+', t)]) == 1:
                    limit = int(token)
                else:
                    ambiguous_two_numbers = True
            else:
                category_name_parts.append(token)
            i += 1
        if ambiguous_two_numbers and not category_name_parts and explicit_category_index is None:
            raise ValueError('Ambiguous list command. Use `bSearch list category <index> <limit>` when both index and limit are needed.')
        context = self._load_context()
        resolved_category = None
        view = 'categories'
        if explicit_category_index is not None:
            categories = context.get('entries', []) if context.get('view') == 'categories' else []
            if not categories or explicit_category_index < 1 or explicit_category_index > len(categories):
                raise ValueError('No recent category list context is available for that index.')
            resolved_category = categories[explicit_category_index - 1]['category']
            view = 'category_items'
        elif category_name_parts:
            resolved_category = ' '.join(category_name_parts)
            view = 'category_items'
        elif len(tokens) == 1 and re.fullmatch(r'\d+', tokens[0]) and context.get('view') == 'categories' and context.get('entries'):
            idx = int(tokens[0])
            if 1 <= idx <= len(context['entries']):
                resolved_category = context['entries'][idx - 1]['category']
                view = 'category_items'
        if view == 'categories':
            entries = self._categories_from_items()
            entries.sort(key=(lambda x: x['category'].lower()) if sort_mode == 'alpha' else (lambda x: (-x['score'], x['category'].lower())))
            if limit is not None:
                entries = entries[:limit]
            result = {'command_family': 'list', 'view': 'categories', 'sort': sort_mode, 'entries': entries}
            self._save_context({'view': 'categories', 'sort': sort_mode, 'entries': entries})
            return result
        items = self._current_items(include_archived=False)
        matched = [item for item in items if item['category'].lower() == resolved_category.lower()]
        if not matched:
            candidates = sorted({item['category'] for item in items})
            fuzzy = [name for name in candidates if resolved_category.lower() in name.lower()]
            if len(fuzzy) == 1:
                resolved_category = fuzzy[0]
                matched = [item for item in items if item['category'] == resolved_category]
            elif not fuzzy:
                historical_categories = {row.get('category', '') for row in self._all_feedback_rows() if row.get('category')}
                if not any(resolved_category.lower() == name.lower() for name in historical_categories):
                    raise ValueError(f'No category matched: {resolved_category}')
            else:
                raise ValueError(f'Ambiguous category reference: {resolved_category}')
        matched.sort(key=(lambda x: x['title'].lower()) if sort_mode == 'alpha' else (lambda x: (-x['score'], x['title'].lower())))
        if not show_all and limit is not None:
            matched = matched[:limit]
        entries = [{'title': item['title'], 'score': item['score'], 'category': item['category']} for item in matched]
        result = {'command_family': 'list', 'view': 'category_items', 'sort': sort_mode, 'resolved_category': resolved_category, 'entries': entries}
        self._save_context({'view': 'category_items', 'sort': sort_mode, 'resolved_category': resolved_category, 'entries': entries})
        return result

    def _handle_rate(self, command: str, remainder: str) -> Dict[str, Any]:
        body = re.sub(r'^(rate|score)\s+', '', remainder, flags=re.IGNORECASE)
        body = re.sub(r'^update score for\s+', '', body, flags=re.IGNORECASE)
        body = re.sub(r'\s+to\s+', ' ', body, flags=re.IGNORECASE)
        reference, score = self._parse_score_and_reference(body)
        item = self._find_item(reference, include_archived=True)
        now = self._now_utc()
        self._record_candidate_delivery_feedback(now=now, run_type='manual_rating', item=item, score=score, comment='manual rating')
        self._rebuild_profile()
        return {'command_family': 'rate', 'item': {'title': item['title'], 'user_feedback_score': score, 'category': item['category']}}

    def _handle_show(self, command: str, remainder: str) -> Dict[str, Any]:
        body = re.sub(r'^(show|open)\s+', '', remainder, flags=re.IGNORECASE)
        body = re.sub(r'^tell me about\s+', '', body, flags=re.IGNORECASE)
        item = self._find_item(body, include_archived=True)
        return {'command_family': 'show', 'item': item}

    def _handle_search_memory(self, command: str, remainder: str) -> Dict[str, Any]:
        body = re.sub(r'^(search memory|find saved)\s*', '', remainder, flags=re.IGNORECASE).strip()
        needle = body.lower()
        matches = []
        for item in self._current_items(include_archived=False):
            haystack = ' '.join([item['title'], item['category'], item['description'], ' '.join(item['links'])]).lower()
            if needle in haystack:
                matches.append({'title': item['title'], 'category': item['category'], 'score': item['score']})
        matches.sort(key=lambda x: (-x['score'], x['title'].lower()))
        self._save_context({'view': 'search_results', 'entries': matches})
        return {'command_family': 'search_memory', 'entries': matches}

    def _handle_review_pending(self, command: str, remainder: str) -> Dict[str, Any]:
        pending_run = self._latest_unhandled_run()
        if pending_run is None:
            return {
                'command_family': 'review_pending',
                'status': 'no_pending_run',
                'message': 'No unhandled bSearch run is waiting for review.',
                'entries': [],
            }
        entries = []
        for title in pending_run['pending_titles']:
            try:
                item = self._find_item(title, include_archived=True)
                entries.append({
                    'title': item['title'],
                    'category': item['category'],
                    'score': item['score'],
                    'source_type': item['source_type'],
                    'description': item.get('description', ''),
                    'links': item.get('links', []),
                })
            except Exception:
                entries.append({'title': title, 'links': []})
        current_item = entries[0] if entries else None
        self._save_context({'view': 'pending_review', 'run_timestamp_utc': pending_run['run_timestamp_utc'], 'entries': entries})
        return {
            'command_family': 'review_pending',
            'status': 'pending_run_ready_for_review',
            'run_timestamp_utc': pending_run['run_timestamp_utc'],
            'pending_count': pending_run['pending_count'],
            'total_count': pending_run['total_count'],
            'entries': entries,
            'current_index': 1 if current_item else 0,
            'current_item': current_item,
            'message': 'Review item 1 first. Use `bSearch score <item> <1-5>` or `bSearch archive <item>` to handle it, then ask for the next item.',
        }

    def _handle_profile(self, command: str, remainder: str) -> Dict[str, Any]:
        profile_path = self.root / 'user-interest-profile.md'
        lowered = remainder.lower()
        if lowered.startswith('show profile'):
            return {'command_family': 'profile', 'profile': profile_path.read_text(encoding='utf-8')}
        text = profile_path.read_text(encoding='utf-8') if profile_path.exists() else '# bSearch user-interest profile\n'
        if lowered.startswith('add interest '):
            text += f"\n- Explicit interest: {remainder[len('add interest '):].strip()}\n"
        elif lowered.startswith('remove interest '):
            interest = remainder[len('remove interest '):].strip().lower()
            text = '\n'.join([line for line in text.splitlines() if interest not in line.lower()]) + '\n'
        elif lowered.startswith('update profile '):
            text += '\n' + remainder[len('update profile '):].strip() + '\n'
        profile_path.write_text(text, encoding='utf-8')
        return {'command_family': 'profile', 'profile': text}

    def _handle_settings(self, command: str, remainder: str) -> Dict[str, Any]:
        lowered = remainder.lower().strip()
        if lowered == 'settings':
            return {'command_family': 'settings', 'config': self._extract_config()}
        body = re.sub(r'^set\s+', '', remainder, flags=re.IGNORECASE)
        text = self._load_config_text()
        changed = None
        if re.match(r'^exploration\s+', body, flags=re.IGNORECASE):
            value = re.sub(r'^exploration\s+', '', body, flags=re.IGNORECASE).strip()
            text = re.sub(r'(^\s*exploration_strength:\s*)([0-9.]+)$', rf'\g<1>{value}', text, flags=re.MULTILINE)
            changed = ('exploration_strength', float(value))
        elif re.match(r'^(candidate pool|candidate_pool|candidate-pool)\s+', body, flags=re.IGNORECASE):
            value = re.sub(r'^(candidate pool|candidate_pool|candidate-pool)\s+', '', body, flags=re.IGNORECASE).strip()
            text = re.sub(r'(^\s*candidate_pool_size:\s*)(\d+)$', rf'\g<1>{value}', text, flags=re.MULTILINE)
            changed = ('candidate_pool_size', int(value))
        elif re.match(r'^(delivered count|delivered_count|delivered-count)\s+', body, flags=re.IGNORECASE):
            value = re.sub(r'^(delivered count|delivered_count|delivered-count)\s+', '', body, flags=re.IGNORECASE).strip()
            text = re.sub(r'(^\s*delivered_item_count:\s*)(\d+)$', rf'\g<1>{value}', text, flags=re.MULTILINE)
            changed = ('delivered_item_count', int(value))
        else:
            raise ValueError(f'Unsupported settings command: {command}')
        self._save_config_text(text)
        return {'command_family': 'settings', 'changed': changed, 'config': self._extract_config()}

    def _handle_remove(self, command: str, remainder: str) -> Dict[str, Any]:
        body = re.sub(r'^(remove|archive)\s+', '', remainder, flags=re.IGNORECASE).strip()
        item = self._find_item(body, include_archived=True)
        now = self._now_utc()
        self._append_jsonl(self.status_file, {'recorded_at_utc': now, 'title': item['title'], 'status': 'archived'})
        self._rebuild_profile()
        return {'command_family': 'remove', 'title': item['title'], 'status': 'archived'}

    def _handle_run(self, command: str, remainder: str) -> Dict[str, Any]:
        pending_run = self._latest_unhandled_run()
        if pending_run is not None:
            return {
                'command_family': 'run',
                'status': 'blocked_unhandled_previous_run',
                'blocked_run_timestamp_utc': pending_run['run_timestamp_utc'],
                'pending_count': pending_run['pending_count'],
                'total_count': pending_run['total_count'],
                'pending_titles': pending_run['pending_titles'],
                'review_command': 'bSearch review pending',
                'message': 'Previous bSearch run still has unhandled delivered items; skipping new run until the user handles them. Use `bSearch review pending` to start scoring or archiving them.',
            }
        config = self._extract_config()
        discovered = self._discover_multisource_candidates(config)
        if not discovered:
            fallback = self._current_items(include_archived=False)
            fallback.sort(key=lambda x: (-x['score'], -x['predicted_interest'], x['title'].lower()))
            discovered = [item | {'candidate_position': index, 'candidate_pool_size': len(fallback), 'rank_progress': round(index / max(len(fallback), 1), 4)} for index, item in enumerate(fallback[:config['candidate_pool_size']], start=1)]
            candidates = discovered
            discovery_mode = 'history_fallback'
            source_strategy = 'history_fallback'
        else:
            scored = self._score_discovered_candidates(discovered, config)
            candidates = self._select_candidates_by_random_source(scored, config)
            discovery_mode = 'multisource_live_discovery'
            source_strategy = 'random_source_per_slot'
        delivered = candidates[:config['delivered_item_count']]
        now = self._now_utc()
        for item in candidates:
            self._record_candidate_delivery_feedback(now=now, run_type='manual_run', item=item, score=None, delivered_to_user=False)
        for item in delivered:
            self._append_delivered_record(now=now, run_type='manual_run', item=item)
        self._write_run_markdown(now, delivered, config, discovery_mode)
        state_text = self._load_state_text()
        if re.search(r'(^\s*last_manual_run:\s*).+$', state_text, flags=re.MULTILINE):
            state_text = re.sub(r'(^\s*last_manual_run:\s*).+$', rf'\g<1>{now}', state_text, flags=re.MULTILINE)
        else:
            state_text += f'\n  last_manual_run: {now}\n'
        self._save_state_text(state_text)
        return {'command_family': 'run', 'run_timestamp_utc': now, 'discovery_mode': discovery_mode, 'source_strategy': source_strategy, 'candidate_titles': [item['title'] for item in candidates], 'delivered_titles': [item['title'] for item in delivered], 'source_types': sorted({item['source_type'] for item in candidates})}

    def _write_run_markdown(self, run_timestamp: str, delivered: List[Dict[str, Any]], config: Dict[str, Any], discovery_mode: str) -> None:
        lines = [
            f'# bSearch manual run — {run_timestamp[:10]}',
            '',
            '```yaml',
            f'run_type: {discovery_mode}',
            f'run_timestamp_utc: {run_timestamp}',
            f"timezone: {config['timezone']}",
            f"candidate_pool_size: {config['candidate_pool_size']}",
            f"delivered_item_count: {len(delivered)}",
            f"exploration_strength: {config['exploration_strength']}",
            '```',
            '',
            '## Shortlist',
        ]
        for idx, item in enumerate(delivered, start=1):
            desc = item['description'].split('. ')[0].strip().rstrip('.')
            lines.append(f"{idx}. **{item['title']}** — {desc}.")
        lines += ['', '## Detailed items']
        for idx, item in enumerate(delivered, start=1):
            lines += ['', f"### {idx}. {item['title']}", f"- Source type: {item['source_type']}", f"- Category: {item['category']}", f"- Predicted interest: {item['predicted_interest']}", f"- Final score: {item['final_score']}", item['description'], '', 'Key links:']
            for link in item.get('links', [])[:3]:
                lines.append(f'- {link}')
        (self.root / 'runs' / f'{run_timestamp[:10]}_run.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv: Optional[List[str]] = None) -> int:
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print('Usage: python bsearch_handler.py "bSearch ..."')
        return 1
    command = ' '.join(argv)
    handler = BSearchHandler(Path(__file__).resolve().parent)
    result = handler.handle(command)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
