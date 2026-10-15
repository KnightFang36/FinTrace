"""Synthetic publisher metadata is separate from detection identities."""
import tempfile
import unittest
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from fintrace.ingestion.publisher import reconcile_publisher_accounts
from fintrace.ingestion.audit import ACCOUNTS_HEADER


class PublisherAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "accounts.csv"
        self.observed = self.root / "observed.parquet"
        rows = [{"schema_version": "1", "run_id": "fixture", "dataset_id": "fixture",
                 "bank_id": bank, "account_id": account}
                for bank, account in (("010", "A"), ("20", "B"), ("30", "C"), ("40", "D"))]
        pq.write_table(pa.Table.from_pylist(rows), self.observed)
        self.source.write_text(
            ",".join(ACCOUNTS_HEADER) + "\n"
            "Bank,10,A,E1,Entity 1\n"
            "Bank,20,B,E2,Entity 2\n"
            "Bank,030,C,E3,Entity 3\n"
            "Bank,30,C,E4,Entity 4\n"
        )
        self.processed = self.root / "processed"

    def test_exact_alias_ambiguous_and_unmatched_are_distinct(self):
        report = reconcile_publisher_accounts(self.source, self.root, self.observed, self.processed)
        self.assertEqual(report["observed_account_status_counts"],
                         {"ambiguous": 1, "exact_source_key": 1, "unmatched": 1, "zero_padding_candidate": 1})
        target = self.processed / "supplemental" / report["snapshot_id"]
        links = pq.read_table(target / "account_link_candidates.parquet").to_pylist()
        alias = next(row for row in links if row["account_id"] == "A")
        self.assertEqual((alias["bank_id"], alias["publisher_bank_id"]), ("010", "10"))
        self.assertNotIn("is_laundering", alias)

    def test_snapshot_is_reused_without_mutating_sources(self):
        original = self.source.read_bytes()
        first = reconcile_publisher_accounts(self.source, self.root, self.observed, self.processed)
        second = reconcile_publisher_accounts(self.source, self.root, self.observed, self.processed)
        self.assertEqual(second["status"], "reused")
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertEqual(self.source.read_bytes(), original)

    def test_invalid_publisher_rows_are_quarantined(self):
        with self.source.open("a") as handle:
            handle.write("broken,row\n")
        report = reconcile_publisher_accounts(self.source, self.root, self.observed, self.processed)
        self.assertEqual(report["publisher_records"], 4)
        self.assertEqual(report["quarantined_publisher_records"], 1)
