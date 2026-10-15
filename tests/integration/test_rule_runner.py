"""Bounded runner integration over handcrafted prepared data."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fintrace.contracts import AccountKey
from fintrace.ingestion.ibm import ingest_ibm
from fintrace.ingestion.manifest import IBM_HEADER, create_manifest, write_manifest
from fintrace.rules.runner import run_rule_snapshot

ROOT = Path(__file__).resolve().parents[2]
CUTOFF = "2022-09-01T01:00:00Z"


class RuleRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.raw = root / "raw"
        self.raw.mkdir()
        source = self.raw / "source.csv"
        source.write_text(
            ",".join(IBM_HEADER) + "\n"
            "2022/09/01 00:05,1,S1,1,A,10.00,USD,10.00,USD,ACH,0\n"
            "2022/09/01 00:10,1,S2,1,A,10.00,USD,10.00,USD,ACH,1\n"
            "2022/09/01 00:20,1,A,1,A,10.00,USD,10.00,USD,Reinvestment,0\n"
            "2022/09/01 01:05,1,S3,1,A,10.00,USD,10.00,USD,ACH,1\n"
        )
        manifest = create_manifest(
            source, self.raw, variant="HI-Small", acquired_at=None,
            timezone_policy="UTC", timestamp_precision="minute", source_terms="Handcrafted fixture",
        )
        manifest_path = write_manifest(manifest, self.raw / "manifest.json", self.raw)
        processed = root / "processed"
        ingest_ibm(manifest_path, self.raw, processed)
        self.path = processed / "datasets" / manifest["dataset_id"] / "transactions.parquet"
        self.evaluation = processed / "evaluation" / manifest["dataset_id"]
        self.policy = root / "rules.toml"
        self.policy.write_text((ROOT / "config/rules.toml").read_text().replace(
            "minimum_distinct_senders = 8", "minimum_distinct_senders = 2",
        ))
        self.output = root / "rule_runs"

    def run_rules(self, **kwargs):
        return run_rule_snapshot(self.path, self.policy, CUTOFF, self.output, **kwargs)

    def test_verified_snapshot_has_evidence_coverage_and_reuse(self):
        result = self.run_rules()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["findings_by_rule"], {"fan_in": 1})
        self.assertEqual(result["input_records"], 3)
        self.assertEqual(result["feature_status"]["burst"], "unavailable")
        evidence = json.loads((Path(result["output_directory"]) / "findings.json").read_text())
        self.assertEqual(len(evidence["findings"][0]["transaction_ids"]), 2)
        self.assertNotIn("is_laundering", json.dumps(evidence))
        self.assertEqual(self.run_rules()["status"], "reused")

    def test_corrupted_evaluation_data_is_never_opened_by_rules(self):
        (self.evaluation / "labels.parquet").write_bytes(b"deliberately invalid evaluation fixture")
        self.assertEqual(self.run_rules()["findings_by_rule"], {"fan_in": 1})

    def test_account_scope_does_not_create_partial_neighbour_findings(self):
        result = self.run_rules(subject_accounts=[AccountKey("1", "S1")])
        self.assertEqual(result["input_records"], 1)
        self.assertEqual(result["finding_count"], 0)

    def test_input_and_output_corruption_are_rejected(self):
        result = self.run_rules()
        with (Path(result["output_directory"]) / "findings.json").open("a") as handle:
            handle.write("changed")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.run_rules()
        with self.path.open("ab") as handle:
            handle.write(b"changed")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.run_rules()

    def test_evaluation_path_is_rejected(self):
        with self.assertRaises(ValueError):
            run_rule_snapshot(self.evaluation / "labels.parquet", self.policy, CUTOFF, self.output)

    def test_incomplete_output_marker_is_not_treated_as_a_reusable_run(self):
        result = self.run_rules()
        path = Path(result["output_directory"]) / "run.json"
        metadata = json.loads(path.read_text())
        metadata["status"] = "incomplete"
        path.write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.run_rules()

    def test_input_limit_fails_without_sampling_or_publishing(self):
        self.policy.write_text(self.policy.read_text().replace("max_input_transactions = 250000",
                                                               "max_input_transactions = 1"))
        with self.assertRaisesRegex(ValueError, "budget"):
            self.run_rules()
        self.assertFalse(self.output.exists())

    def test_cli_runs_snapshot_and_reports_dependency_errors(self):
        command = [
            sys.executable, str(ROOT / "scripts/run_rules.py"), str(self.path),
            "--policy", str(self.policy), "--cutoff", CUTOFF, "--output-root", str(self.output),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["findings_by_rule"], {"fan_in": 1})
        result = subprocess.run(command[:1] + ["-S"] + command[1:], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("config/data-requirements.txt", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
