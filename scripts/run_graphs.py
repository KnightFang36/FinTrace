"""Analyze and visualize a bounded verified NetworkX transaction snapshot."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# Keep plotting cache inside the workspace; never require writes to the home directory.
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transactions", type=Path)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--policy", type=Path, default=ROOT / "config/graph.toml")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/processed/graph_runs")
    parser.add_argument("--seed", nargs=2, action="append", default=[], metavar=("BANK_ID", "ACCOUNT_ID"))
    args = parser.parse_args(argv)
    try:
        from fintrace.graph.runner import run_graph_snapshot
        result = run_graph_snapshot(args.transactions, args.policy, args.cutoff, args.output_root,
                                    seed_accounts=[{"bank_id": bank, "account_id": account} for bank, account in args.seed])
    except ImportError as error:
        print(f"Graph dependencies unavailable: {error}. Install config/data-requirements.txt", file=sys.stderr)
        return 2
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Graph analysis failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
