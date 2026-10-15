"""Exercise local provenance CLI against handcrafted temporary CSVs."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from fintrace.ingestion.manifest import IBM_HEADER


class PrepareDataCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.raw = Path(temporary.name)
        self.source = self.raw / "source.csv"
        self.source.write_text(",".join(IBM_HEADER) + "\n", encoding="utf-8")
        self.base = [sys.executable, str(ROOT / "scripts/prepare_data.py"), "--raw-root", str(self.raw)]
        self.create_args = [
            "create", str(self.source), "--variant", "HI-Small",
            "--acquired-at", "2026-10-15T12:00:00Z", "--timezone", "UTC",
            "--timestamp-precision", "minute",
            "--source-terms", "Handcrafted test fixture, not IBM benchmark data",
        ]

    def run_cli(self, arguments):
        return subprocess.run(self.base + arguments, text=True, capture_output=True, check=False)

    def test_create_then_verify_and_refuse_replacement(self):
        result = self.run_cli(self.create_args)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "created")
        self.assertEqual(payload["coverage"], "unknown")
        verified = self.run_cli(["verify", str(self.raw / "manifest.json")])
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["dataset_id"], payload["dataset_id"])
        repeated = self.run_cli(self.create_args)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("File exists", repeated.stderr)

    def test_altered_file_fails_verification(self):
        self.assertEqual(self.run_cli(self.create_args).returncode, 0)
        with self.source.open("a") as handle:
            handle.write("changed bytes\n")
        result = self.run_cli(["verify", str(self.raw / "manifest.json")])
        self.assertEqual(result.returncode, 2)
        self.assertIn("integrity mismatch", result.stderr)

    def test_missing_source_does_not_create_manifest(self):
        self.source.unlink()
        result = self.run_cli(self.create_args)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.raw / "manifest.json").exists())

    def test_ingestion_without_optional_dependencies_has_actionable_error(self):
        self.assertEqual(self.run_cli(self.create_args).returncode, 0)
        result = subprocess.run([
            sys.executable, "-S", str(ROOT / "scripts/prepare_data.py"),
            "--raw-root", str(self.raw), "ingest", str(self.raw / "manifest.json"),
        ], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("config/data-requirements.txt", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
