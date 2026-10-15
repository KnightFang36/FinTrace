"""Handcrafted upload inventory cases; no publisher records bundled."""
import tempfile
import unittest
from pathlib import Path
from fintrace.ingestion.audit import ACCOUNTS_HEADER, audit_sources
from fintrace.ingestion.manifest import IBM_HEADER, ManifestError


class SourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.row = "2022/09/01 00:00,010,A,001,B,1.00,US Dollar,1.00,US Dollar,ACH,0"
        (self.root / "transactions.csv").write_text(",".join(IBM_HEADER) + "\n" + self.row + "\n")
        (self.root / "accounts.csv").write_text(",".join(ACCOUNTS_HEADER) + "\nBank,10,A,E,Entity\n")
        (self.root / "Pattern.txt").write_text(
            "BEGIN LAUNDERING ATTEMPT - TEST\n" + self.row + "\nEND LAUNDERING ATTEMPT - TEST\n"
        )

    def test_counts_sources_without_inventing_metadata(self):
        result = audit_sources(self.root, "transactions.csv", "accounts.csv", "Pattern.txt")
        self.assertEqual(result["transactions"]["record_count"], 1)
        self.assertEqual(result["publisher_accounts"]["record_count"], 1)
        self.assertEqual(result["evaluation_only_patterns"]["attempts_started"], 1)
        self.assertIsNone(result["acquired_at"])
        self.assertIsNone(result["timezone_policy"])
        self.assertEqual(result["observation_coverage"], "unknown")
        self.assertNotIn("is_laundering", result["transactions"])

    def test_bad_rows_and_unclosed_pattern_are_reported(self):
        with (self.root / "transactions.csv").open("a") as handle:
            handle.write("broken,row\n")
        (self.root / "Pattern.txt").write_text("BEGIN LAUNDERING ATTEMPT - TEST\n")
        result = audit_sources(self.root, "transactions.csv", patterns="Pattern.txt")
        self.assertEqual(result["transactions"]["wrong_width_records"], 1)
        self.assertEqual(result["evaluation_only_patterns"]["malformed_records"], 1)

    def test_wrong_accounts_header_is_rejected(self):
        (self.root / "accounts.csv").write_text("unexpected\n")
        with self.assertRaisesRegex(ManifestError, "accounts header"):
            audit_sources(self.root, "transactions.csv", "accounts.csv")
