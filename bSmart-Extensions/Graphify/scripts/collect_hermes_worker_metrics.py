#!/usr/bin/env python3
"""Collect Hermes subagent worker metrics for controlled evaluations.

Usage:
  python scripts/collect_hermes_worker_metrics.py \
    --state-db /opt/data/state.db \
    --phase baseline:20260718_134049_b92618,149.63 \
    --phase graphify:20260718_135449_580e71,165.80

Each --phase entry is NAME:SESSION_ID,SECONDS. Repeat for each worker.
Approval-task rows are reported separately from main model rows.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import defaultdict


def parse_phase(raw: str):
    name, rest = raw.split(':', 1)
    sid, sec = rest.split(',', 1)
    return name, sid, float(sec)


def add_row(acc, row):
    acc['api_calls'] += row['api_call_count']
    acc['input_tokens'] += row['input_tokens']
    acc['output_tokens'] += row['output_tokens']
    acc['cache_read_tokens'] += row['cache_read_tokens']
    acc['cache_write_tokens'] += row['cache_write_tokens']
    acc['reasoning_tokens'] += row['reasoning_tokens']
    acc['total_tokens'] += (
        row['input_tokens'] + row['output_tokens'] + row['cache_read_tokens']
        + row['cache_write_tokens'] + row['reasoning_tokens']
    )


def empty_acc():
    return defaultdict(int)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--state-db', default='/opt/data/state.db')
    ap.add_argument('--phase', action='append', required=True, help='NAME:SESSION_ID,SECONDS')
    args = ap.parse_args()

    phases = defaultdict(list)
    for item in args.phase:
        name, sid, sec = parse_phase(item)
        phases[name].append((sid, sec))

    con = sqlite3.connect(args.state_db)
    con.row_factory = sqlite3.Row
    report = {}
    for name, workers in phases.items():
        main_acc = empty_acc()
        approval_acc = empty_acc()
        per_worker = []
        for idx, (sid, sec) in enumerate(workers, 1):
            rows = [dict(r) for r in con.execute(
                'select * from session_model_usage where session_id=?', (sid,)
            )]
            worker_acc = empty_acc()
            for row in rows:
                if row.get('task') == 'approval':
                    add_row(approval_acc, row)
                else:
                    add_row(main_acc, row)
                    add_row(worker_acc, row)
            per_worker.append({'worker': idx, 'session_id': sid, 'seconds': sec, **dict(worker_acc)})
        secs = [sec for _, sec in workers]
        report[name] = {
            'workers': len(workers),
            'aggregate': {**dict(main_acc), 'avg_worker_seconds': statistics.mean(secs), 'sum_worker_seconds': sum(secs)},
            'approval_overhead': dict(approval_acc),
            'per_worker': per_worker,
        }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
