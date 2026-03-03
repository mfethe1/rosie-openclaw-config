#!/usr/bin/env python3
import argparse, datetime as dt, json, os, pathlib

PATHS = [
    pathlib.Path('/Volumes/EDrive-1'),
    pathlib.Path('/Volumes/Edrive'),
    pathlib.Path('/home/michael-fethe/agent_coordination'),
]


def check_root():
    for p in PATHS:
        if p.exists():
            return p
    return None


def run():
    root = check_root()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    report = {
        'ts': now,
        'root_found': str(root) if root else None,
        'mount_available': bool(root),
        'kpis': {
            'status_freshness_under_12h_pct': None,
            'three_identical_cron_pause_count': None,
            'mount_mttr_minutes': None,
            'blockers_over_24h_count': None,
            'same_day_revenue_blocker_resolution_pct': None,
        },
        'checks': {}
    }

    if root:
        for f in ['AGENTS.md', 'SOUL.md', 'HEARTBEAT.md']:
            fp = root / f
            report['checks'][f] = {'exists': fp.exists(), 'path': str(fp)}
    else:
        report['checks']['error'] = 'No shared root mounted in resolution order'

    outdir = pathlib.Path('/Users/harrisonfethe/.openclaw/workspace/self_improvement/outputs')
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"drift-report-{dt.datetime.now().strftime('%Y%m%d-%H%M')}.json"
    out.write_text(json.dumps(report, indent=2))
    print(str(out))


def tests():
    assert PATHS[0].is_absolute()
    print('ok')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', action='store_true')
    args = ap.parse_args()
    if args.test:
        tests()
    else:
        run()
