"""Read cases or apply one explicit version-checked, idempotent case action."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT/'data/processed/alerts.duckdb')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list')
    show = commands.add_parser('show'); show.add_argument('case_id'); show.add_argument('--version', type=int)
    apply = commands.add_parser('apply')
    apply.add_argument('action', choices=['create', 'attach', 'note', 'assign', 'transition', 'reopen'])
    apply.add_argument('--case-id'); apply.add_argument('--expected-version', required=True, type=int)
    apply.add_argument('--payload-file', type=Path); apply.add_argument('--request-id', required=True)
    for name in ['actor', 'at', 'reason']:
        apply.add_argument('--'+name, required=True)
    args = parser.parse_args(argv)
    try:
        import duckdb
        from fintrace.cases.service import apply_case_action
        from fintrace.storage.case_store import read_cases
        if args.command == 'list':
            value = read_cases(args.database)
        elif args.command == 'show':
            value = read_cases(args.database, args.case_id, version=args.version)
        else:
            payload = json.loads(args.payload_file.read_text()) if args.payload_file else {}
            value = apply_case_action(args.database, args.case_id, args.action, actor=args.actor, at=args.at,
                reason=args.reason, expected_version=args.expected_version, request_id=args.request_id, payload=payload)
    except ImportError as error:
        print(f'Data dependencies unavailable: {error}', file=sys.stderr); return 2
    except (ValueError, OSError, KeyError, TypeError, duckdb.Error) as error:
        print(f'Case operation failed: {error}', file=sys.stderr); return 2
    print(json.dumps(value, indent=2)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
