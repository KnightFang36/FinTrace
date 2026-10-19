"""Export a verified snapshot/alert scope or frozen case version to local artifacts."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT/'data/processed/alerts.duckdb')
    parser.add_argument('--processed-root', type=Path, default=ROOT/'data/processed')
    parser.add_argument('--output-root', type=Path, default=ROOT/'outputs')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--snapshot'); group.add_argument('--case')
    parser.add_argument('--case-version', type=int); parser.add_argument('--alert', action='append', default=[])
    parser.add_argument('--formats', nargs='+', choices=['json', 'csv', 'html', 'png'], default=['json', 'csv', 'html', 'png'])
    parser.add_argument('--at', required=True)
    args = parser.parse_args(argv)
    try:
        import duckdb
        from fintrace.reporting.export import export_evidence
        value = export_evidence(args.database, args.processed_root, args.output_root, snapshot_id=args.snapshot,
            alert_ids=args.alert, case_id=args.case, case_version=args.case_version, formats=args.formats, at=args.at)
    except ImportError as error:
        print(f'Data dependencies unavailable: {error}', file=sys.stderr); return 2
    except (ValueError, OSError, KeyError, TypeError, duckdb.Error) as error:
        print(f'Report export failed: {error}', file=sys.stderr); return 2
    print(json.dumps(value, indent=2)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
