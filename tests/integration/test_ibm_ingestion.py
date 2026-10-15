"""End-to-end Parquet imports using handcrafted source files only."""
import csv
import json
import tempfile
from pathlib import Path
import unittest
import pyarrow.parquet as pq
from fintrace.ingestion.ibm import ingest_ibm
from fintrace.ingestion.manifest import IBM_HEADER, ManifestError, create_manifest, write_manifest


class IbmIngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw, self.processed = self.root / "raw", self.root / "processed"
        self.raw.mkdir()
        self.source = self.raw / "source.csv"

    def prepare(self, rows):
        self.source.write_text(",".join(IBM_HEADER) + "\n" + "\n".join(rows) + ("\n" if rows else ""))
        manifest = create_manifest(
            self.source, self.raw, variant="HI-Small", acquired_at="2026-10-16T00:00:00Z",
            timezone_policy="UTC", timestamp_precision="minute", source_terms="Handcrafted fixture",
        )
        self.manifest = write_manifest(manifest, self.raw / "manifest.json", self.raw)
        self.dataset = self.processed / "datasets" / manifest["dataset_id"]
        self.evaluation = self.processed / "evaluation" / manifest["dataset_id"]

    def normal(self, label="0"):
        return "2022/09/01 00:00,010,000A,001,000B,1.10,US Dollar,0.00000001,Bitcoin,Wire," + label

    def test_precision_lineage_duplicate_retention_and_label_isolation(self):
        self.prepare([self.normal("0"), self.normal("1")])
        result = ingest_ibm(self.manifest, self.raw, self.processed, batch_size=1)
        self.assertEqual(result["status"], "completed")
        table = pq.read_table(self.dataset / "transactions.parquet")
        rows = table.to_pylist()
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["transaction_id"], rows[1]["transaction_id"])
        self.assertEqual(rows[0]["source_row_hash"], rows[1]["source_row_hash"])
        self.assertEqual(rows[0]["sender_bank_id"], "010")
        self.assertEqual(str(rows[0]["amount_paid"]), "1E-8")
        self.assertNotIn("is_laundering", table.column_names)
        self.assertEqual(pq.read_table(self.evaluation / "labels.parquet").num_rows, 2)
        accounts = pq.read_table(self.dataset / "accounts.parquet").to_pylist()
        self.assertEqual({(r["bank_id"], r["account_id"]) for r in accounts}, {("010", "000A"), ("001", "000B")})
        quality = json.loads((self.dataset / "quality.json").read_text())
        self.assertEqual(quality["duplicate_financial_records"], 1)
        self.assertEqual(quality["history_eligibility"], "requires_explicit_coverage")
        self.assertEqual(quality["source_records"], quality["accepted_records"] + quality["quarantined_records"])

    def test_invalid_amount_is_quarantined_without_label_in_detection_files(self):
        self.prepare([self.normal(), self.normal("1").replace(",1.10,", ",NaN,")])
        ingest_ibm(self.manifest, self.raw, self.processed)
        self.assertEqual(pq.read_table(self.dataset / "transactions.parquet").num_rows, 1)
        rejected = pq.read_table(self.dataset / "quarantine.parquet").to_pylist()
        self.assertEqual(rejected[0]["source_record_number"], 2)
        self.assertIn("invalid_amount", rejected[0]["issue_codes"])
        self.assertEqual(len(json.loads(rejected[0]["financial_fields_json"])), 10)
        self.assertNotIn("is_laundering", rejected[0])

    def test_invalid_or_missing_labels_do_not_reject_valid_financial_rows(self):
        self.prepare([self.normal("invalid"), self.normal().rsplit(",", 1)[0]])
        ingest_ibm(self.manifest, self.raw, self.processed)
        self.assertEqual(pq.read_table(self.dataset / "transactions.parquet").num_rows, 2)
        self.assertEqual(pq.read_table(self.evaluation / "labels.parquet").num_rows, 0)
        self.assertEqual(pq.read_table(self.evaluation / "label_issues.parquet").num_rows, 2)

    def test_completed_import_is_idempotent_and_tampering_is_detected(self):
        self.prepare([self.normal()])
        first = ingest_ibm(self.manifest, self.raw, self.processed)
        second = ingest_ibm(self.manifest, self.raw, self.processed)
        self.assertEqual(second["status"], "reused")
        self.assertEqual(first["run_id"], second["run_id"])
        with (self.dataset / "transactions.parquet").open("ab") as handle:
            handle.write(b"changed")
        with self.assertRaisesRegex(ManifestError, "integrity mismatch"):
            ingest_ibm(self.manifest, self.raw, self.processed)

    def test_empty_import_retains_all_parquet_schemas(self):
        self.prepare([])
        ingest_ibm(self.manifest, self.raw, self.processed)
        for root, name in ((self.dataset, "transactions"), (self.dataset, "quarantine"),
                           (self.dataset, "accounts"), (self.evaluation, "labels")):
            table = pq.read_table(root / (name + ".parquet"))
            self.assertEqual(table.num_rows, 0)
            self.assertGreater(len(table.column_names), 0)

    def test_unrecoverable_csv_error_publishes_no_completed_dataset(self):
        self.prepare(['"unclosed quote'])
        with self.assertRaises(csv.Error):
            ingest_ibm(self.manifest, self.raw, self.processed)
        self.assertFalse(self.dataset.exists())
        self.assertFalse(self.evaluation.exists())
        self.assertEqual(list(self.processed.glob(".ingest-*")), [])
        self.assertEqual(list(self.processed.glob("*.lock")), [])

    def test_invalid_batch_size_is_rejected(self):
        self.prepare([])
        with self.assertRaises(ValueError):
            ingest_ibm(self.manifest, self.raw, self.processed, batch_size=0)

    def test_incomplete_marker_cannot_skip_integrity_verification(self):
        self.prepare([self.normal()])
        ingest_ibm(self.manifest, self.raw, self.processed)
        marker = self.dataset / "completion.json"
        value = json.loads(marker.read_text())
        value["detection_artifacts"] = []
        marker.write_text(json.dumps(value))
        with self.assertRaisesRegex(ManifestError, "Incomplete artifact"):
            ingest_ibm(self.manifest, self.raw, self.processed)

    def test_symlinked_output_parent_is_rejected(self):
        self.prepare([])
        self.processed.mkdir()
        (self.processed / "datasets").symlink_to(self.raw, target_is_directory=True)
        with self.assertRaisesRegex(ManifestError, "symbolic"):
            ingest_ibm(self.manifest, self.raw, self.processed)
