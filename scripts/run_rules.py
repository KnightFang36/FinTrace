"""Evaluate a bounded deterministic snapshot of prepared transaction data."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transactions", type=Path, help="Completed detection transactions.parquet")
    parser.add_argument("--cutoff", required=True, help="Exclusive ISO cutoff with explicit timezone offset")
    parser.add_argument("--policy", type=Path, default=ROOT / "config/rules.toml")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/processed/rule_runs")
    parser.add_argument("--account", nargs=2, action="append", default=[], metavar=("BANK_ID", "ACCOUNT_ID"))
    args = parser.parse_args(argv)
    try:
        from fintrace.rules.runner import run_rule_snapshot
        result = run_rule_snapshot(
            args.transactions, args.policy, args.cutoff, args.output_root,
            subject_accounts=[{"bank_id": bank, "account_id": account} for bank, account in args.account],
        )
    except ImportError as error:
        print(f"Rule dependencies unavailable: {error}. Install config/data-requirements.txt.", file=sys.stderr)
        return 2
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Rule analysis failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
