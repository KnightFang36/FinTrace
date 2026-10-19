"""Replay a bounded schedule of historical cutoffs into a separate audited alert store."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transactions', type=Path)
    parser.add_argument('--start', required=True); parser.add_argument('--end', required=True)
    parser.add_argument('--step-minutes', type=int, required=True)
    parser.add_argument('--actor', required=True); parser.add_argument('--at', required=True)
    parser.add_argument('--rule-policy', type=Path, default=ROOT/'config/rules.toml')
    parser.add_argument('--graph-policy', type=Path, default=ROOT/'config/graph.toml')
    parser.add_argument('--scoring-policy', type=Path, default=ROOT/'config/scoring.toml')
    parser.add_argument('--alert-policy', type=Path, default=ROOT/'config/alerts.toml')
    parser.add_argument('--no-graph', action='store_true')
    parser.add_argument('--output-root', type=Path, default=ROOT/'data/processed/replays')
    parser.add_argument('--checkpoint', type=Path); parser.add_argument('--max-steps', type=int)
    args = parser.parse_args(argv)
    try:
        import duckdb
        from fintrace.replay.engine import replay_transactions
        value = replay_transactions(args.transactions, args.rule_policy, args.scoring_policy, args.alert_policy,
            args.output_root, start=args.start, end=args.end, step_minutes=args.step_minutes, actor=args.actor, at=args.at,
            graph_policy=None if args.no_graph else args.graph_policy, checkpoint=args.checkpoint, max_steps=args.max_steps)
    except ImportError as error:
        print(f'Data dependencies unavailable: {error}', file=sys.stderr); return 2
    except (ValueError, OSError, KeyError, TypeError, duckdb.Error) as error:
        print(f'Historical replay failed: {error}', file=sys.stderr); return 2
    print(json.dumps(value, indent=2)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
