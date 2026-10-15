"""Import verified rule/graph evidence or perform an audited local alert transition."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data/processed/alerts.duckdb")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("import")
    ingest.add_argument("--rules-run", required=True, type=Path)
    ingest.add_argument("--graph-run", type=Path)
    ingest.add_argument("--scoring-policy", type=Path, default=ROOT / "config/scoring.toml")
    ingest.add_argument("--alert-policy", type=Path, default=ROOT / "config/alerts.toml")
    for name in ("import", "transition"):
        command = ingest if name == "import" else commands.add_parser(name)
        command.add_argument("--actor", required=True)
        command.add_argument("--at", required=True, help="Explicit timezone-aware audit instant")
        if name == "transition":
            command.add_argument("alert_id")
            command.add_argument("new_state", choices=("open", "in_review", "escalated", "closed"))
            command.add_argument("--expected-version", required=True, type=int)
            command.add_argument("--reason", required=True)
            command.add_argument("--reopen", action="store_true")
    commands.add_parser("list")
    args = parser.parse_args(argv)
    try:
        if args.command == "import":
            from fintrace.alerts.runner import import_analysis
            result = import_analysis(args.rules_run, args.graph_run, args.scoring_policy, args.alert_policy,
                                     args.database, actor=args.actor, at=args.at)
        else:
            from fintrace.storage.alert_store import AlertStore
            with AlertStore(args.database) as store:
                if args.command == "list":
                    result = {"alerts": store.list_alerts()}
                else:
                    result = store.transition(args.alert_id, args.new_state, actor=args.actor, at=args.at,
                                              reason=args.reason, expected_version=args.expected_version, reopen=args.reopen)
    except ImportError as error:
        print(f"Alert dependencies unavailable: {error}. Install config/data-requirements.txt", file=sys.stderr)
        return 2
    except (ValueError, OSError, KeyError) as error:
        print(f"Alert operation failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
