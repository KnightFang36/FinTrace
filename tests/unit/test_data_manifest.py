"""Handcrafted source examples test provenance; none are IBM benchmark records."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from fintrace.ingestion.manifest import (
    IBM_HEADER, ManifestError, create_manifest, inspect_source, load_manifest,
    validate_manifest, verify_manifest, write_manifest,
)


class DataManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "HI-Small_Trans.csv"
        # Deliberately handcrafted; tests metadata integrity, not detection.
        self.payload = (
            ",".join(IBM_HEADER) + "\n"
            "2022/09/01 00:00,001,00001,002,00002,10.00,USD,10.00,USD,ACH,0\n"
        ).encode()
        self.source.write_bytes(self.payload)
        self.options = dict(
            variant="HI-Small", acquired_at="2026-10-15T12:00:00+00:00",
            timezone_policy="UTC", timestamp_precision="minute",
            source_terms="Handcrafted test fixture; not publisher data",
        )

    def manifest(self, **overrides):
        return create_manifest(self.source, self.root, **(self.options | overrides))

    def test_source_hash_header_and_bytes_preserve_original(self):
        manifest = self.manifest()
        record = manifest["source_files"][0]
        self.assertEqual(record["sha256"], hashlib.sha256(self.payload).hexdigest())
        self.assertEqual(record["byte_count"], len(self.payload))
        self.assertEqual(record["header"].count("Account"), 2)
        self.assertEqual(self.source.read_bytes(), self.payload)
        self.assertEqual(manifest["observation_intervals"], [])
        self.assertNotIn("is_laundering", manifest)

    def test_manifest_roundtrip_verifies_source(self):
        manifest = self.manifest()
        target = write_manifest(manifest, self.root / "manifest.json", self.root)
        self.assertEqual(verify_manifest(target, self.root), manifest)

    def test_identity_is_reproducible_but_policy_changes_identity(self):
        first = self.manifest()
        self.assertEqual(
            first["dataset_id"],
            self.manifest(acquired_at="2026-10-16T12:00:00+00:00")["dataset_id"],
        )
        self.assertNotEqual(
            first["dataset_id"], self.manifest(timezone_policy="Asia/Kolkata")["dataset_id"],
        )

    def test_rejects_renamed_or_reordered_duplicate_header(self):
        self.source.write_bytes(self.payload.replace(b"To Bank,Account", b"To Bank,Account.1"))
        with self.assertRaisesRegex(ManifestError, "header mismatch"):
            self.manifest()

    def test_accepts_utf8_bom_without_editing_source(self):
        self.source.write_bytes(b"\xef\xbb\xbf" + self.payload)
        record = inspect_source(self.source, self.root)
        self.assertEqual(record["byte_count"], len(self.payload) + 3)
        self.assertTrue(self.source.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_detects_changed_source_even_with_same_length(self):
        target = write_manifest(self.manifest(), self.root / "manifest.json", self.root)
        self.source.write_bytes(self.payload.replace(b"10.00", b"11.00"))
        with self.assertRaisesRegex(ManifestError, "integrity mismatch"):
            verify_manifest(target, self.root)

    def test_rejects_empty_or_unknown_timezone(self):
        for value in ("", "UNSET", "Not/A_Timezone"):
            with self.subTest(timezone=value), self.assertRaises(ManifestError):
                self.manifest(timezone_policy=value)

    def test_requires_offset_in_acquisition_time(self):
        with self.assertRaisesRegex(ManifestError, "explicit UTC offset"):
            self.manifest(acquired_at="2026-10-15T12:00:00")

    def test_requires_supported_precision_and_actual_terms(self):
        for override in ({"timestamp_precision": "unknown"}, {"source_terms": ""}):
            with self.subTest(override=override), self.assertRaises(ManifestError):
                self.manifest(**override)

    def test_rejects_invalid_intervals(self):
        for intervals in (
            [{"start": "2022-09-02T00:00:00Z", "end": "2022-09-01T00:00:00Z"}],
            [{"start": "2022-09-01T00:00:00", "end": "2022-09-02T00:00:00"}],
            [
                {"start": "2022-09-01T00:00:00Z", "end": "2022-09-03T00:00:00Z"},
                {"start": "2022-09-02T00:00:00Z", "end": "2022-09-04T00:00:00Z"},
            ],
        ):
            with self.subTest(intervals=intervals), self.assertRaises(ManifestError):
                self.manifest(observation_intervals=intervals)

    def test_accepts_explicit_coverage_and_internal_gap(self):
        coverage = [{"start": "2022-09-01T00:00:00Z", "end": "2022-09-03T00:00:00Z"}]
        gap = [{"start": "2022-09-02T00:00:00Z", "end": "2022-09-02T01:00:00Z"}]
        manifest = self.manifest(observation_intervals=coverage, known_gaps=gap)
        self.assertEqual(manifest["known_gaps"], gap)

    def test_rejects_gap_outside_declared_coverage(self):
        with self.assertRaisesRegex(ManifestError, "within"):
            self.manifest(
                observation_intervals=[{"start": "2022-09-01T00:00:00Z", "end": "2022-09-02T00:00:00Z"}],
                known_gaps=[{"start": "2022-09-03T00:00:00Z", "end": "2022-09-04T00:00:00Z"}],
            )

    def test_refuses_manifest_overwrite(self):
        target = write_manifest(self.manifest(), self.root / "manifest.json", self.root)
        original = target.read_bytes()
        with self.assertRaises(FileExistsError):
            write_manifest(self.manifest(), target, self.root)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(list(self.root.glob(".manifest-*")), [])

    def test_rejects_source_and_output_outside_root(self):
        nested = self.root / "nested"
        nested.mkdir()
        with self.assertRaisesRegex(ManifestError, "inside"):
            create_manifest(self.source, nested, **self.options)
        with self.assertRaisesRegex(ManifestError, "within"):
            write_manifest(self.manifest(), self.root.parent / "outside.json", self.root)

    def test_rejects_symlink_source(self):
        link = self.root / "linked.csv"
        link.symlink_to(self.source)
        with self.assertRaisesRegex(ManifestError, "symbolic"):
            inspect_source(link, self.root)

    def test_rejects_traversal_and_changed_identity(self):
        for relative in ("../outside.csv", "/tmp/outside.csv", "nested/../source.csv", r"nested\source.csv"):
            manifest = copy.deepcopy(self.manifest())
            manifest["source_files"][0]["relative_path"] = relative
            with self.subTest(relative=relative), self.assertRaises(ManifestError):
                validate_manifest(manifest)
        manifest = self.manifest()
        manifest["timezone_policy"] = "Asia/Kolkata"
        with self.assertRaisesRegex(ManifestError, "dataset_id"):
            validate_manifest(manifest)

    def test_rejects_duplicate_json_keys_and_unknown_fields(self):
        target = self.root / "duplicate.json"
        target.write_text('{"schema_version":"1","schema_version":"2"}')
        with self.assertRaisesRegex(ManifestError, "Duplicate"):
            load_manifest(target)
        manifest = self.manifest()
        manifest["extra"] = "unexpected"
        with self.assertRaisesRegex(ManifestError, "fields"):
            validate_manifest(manifest)

    def test_rejects_boolean_byte_count(self):
        manifest = self.manifest()
        manifest["source_files"][0]["byte_count"] = True
        with self.assertRaisesRegex(ManifestError, "positive integer"):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
