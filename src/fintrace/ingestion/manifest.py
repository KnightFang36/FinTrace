"""Verify immutable IBM source files and create reproducible provenance manifests.

Only headers and file metadata are inspected here. Financial row validation,
normalization, and evaluation-label extraction belong to the later CSV adapter.
All functions operate locally and require explicit source interpretation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

IBM_HEADER = (
    "Timestamp", "From Bank", "Account", "To Bank", "Account",
    "Amount Received", "Receiving Currency", "Amount Paid",
    "Payment Currency", "Payment Format", "Is Laundering",
)
VARIANTS = tuple(f"{ratio}-{size}" for ratio in ("HI", "LI") for size in ("Small", "Medium", "Large"))
SOURCE_URL = "https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml"
MANIFEST_FIELDS = {
    "schema_version", "dataset_id", "variant", "synthetic", "source_url",
    "acquired_at", "source_terms", "timezone_policy", "timestamp_precision",
    "normalization_version", "observation_intervals", "known_gaps", "source_files",
}
SOURCE_FIELDS = {"relative_path", "sha256", "byte_count", "header"}
IDENTITY_FIELDS = (
    "variant", "source_files", "timezone_policy", "timestamp_precision",
    "normalization_version", "observation_intervals", "known_gaps",
)


class ManifestError(ValueError):
    """A source or manifest violates its documented provenance contract."""


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{field} must be non-empty text")
    return value


def _instant(value: Any, field: str) -> datetime:
    _required_text(value, field)
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ManifestError(f"{field} must be an ISO timestamp with an offset") from error
    if instant.utcoffset() is None:
        raise ManifestError(f"{field} must include an explicit UTC offset")
    return instant


def _check_intervals(value: Any, field: str) -> list[tuple[datetime, datetime]]:
    if not isinstance(value, list):
        raise ManifestError(f"{field} must be a list")
    parsed = []
    for index, interval in enumerate(value):
        if not isinstance(interval, dict) or set(interval) != {"start", "end"}:
            raise ManifestError(f"{field}[{index}] must contain only start and end")
        start = _instant(interval["start"], f"{field}[{index}].start")
        end = _instant(interval["end"], f"{field}[{index}].end")
        if start >= end:
            raise ManifestError(f"{field}[{index}] must have start before end")
        parsed.append((start, end))
    # Canonical list ordering is required, rather than silently changing declarations.
    if parsed != sorted(parsed):
        raise ManifestError(f"{field} must be sorted by start")
    if any(left[1] > right[0] for left, right in zip(parsed, parsed[1:])):
        raise ManifestError(f"{field} must not overlap")
    return parsed


def _source_path(raw_root: Path, relative_path: str) -> Path:
    _required_text(relative_path, "source relative_path")
    relative = PurePosixPath(relative_path)
    if (
        relative.is_absolute() or ".." in relative.parts
        or "\\" in relative_path or str(relative) != relative_path
    ):
        raise ManifestError("Source path must be canonical and relative to the raw directory")
    root = Path(raw_root).resolve(strict=True)
    path = root.joinpath(*relative.parts)
    if path.is_symlink():
        raise ManifestError("Source files must not be symbolic links")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ManifestError("Source must be a regular file within the raw directory")
    return resolved


def inspect_source(source_path: Path, raw_root: Path) -> dict[str, Any]:
    """Verify ordered duplicate-column header; hash source bytes without editing."""
    root = Path(raw_root).resolve(strict=True)
    supplied = Path(source_path)
    if supplied.is_symlink():
        raise ManifestError("Source files must not be symbolic links")
    path = supplied.resolve(strict=True)
    if not path.is_relative_to(root):
        raise ManifestError("Source must be inside the raw directory")
    relative = path.relative_to(root).as_posix()
    path = _source_path(root, relative)
    before = path.stat()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle), None)
    except (UnicodeError, csv.Error) as error:
        raise ManifestError("Source header is not readable UTF-8 CSV") from error
    if header != list(IBM_HEADER):
        raise ManifestError("IBM header mismatch: exact ordered columns, including both Account columns, are required")
    digest = hashlib.sha256()
    byte_count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            byte_count += len(chunk)
    after = path.stat()
    signature = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    if signature(before) != signature(after) or byte_count != after.st_size:
        raise ManifestError("Source changed during inspection; no manifest can be created")
    return {
        "relative_path": relative,
        "sha256": digest.hexdigest(),
        "byte_count": byte_count,
        "header": header,
    }


def _dataset_id(manifest: dict[str, Any]) -> str:
    identity = {field: manifest[field] for field in IDENTITY_FIELDS}
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "ibm-" + hashlib.sha256(encoded).hexdigest()


def validate_manifest(manifest: Any) -> dict[str, Any]:
    """Validate the version-1 single-CSV contract and its reproducible identity."""
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise ManifestError("Manifest fields do not match the version-1 contract")
    if manifest["schema_version"] != "1" or manifest["synthetic"] is not True:
        raise ManifestError("Expected version 1 and synthetic=true")
    if manifest["variant"] not in VARIANTS:
        raise ManifestError("Unknown IBM dataset variant")
    for field in ("source_url", "source_terms", "normalization_version", "timezone_policy"):
        _required_text(manifest[field], field)
    if not re.match(r"^https://[^/\s]+(?:/|$)", manifest["source_url"]):
        raise ManifestError("source_url must be a public HTTPS source reference")
    _instant(manifest["acquired_at"], "acquired_at")
    try:
        ZoneInfo(manifest["timezone_policy"])
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ManifestError("timezone_policy must be an explicit installed IANA timezone, such as UTC") from error
    if manifest["timestamp_precision"] not in ("minute", "second"):
        raise ManifestError("timestamp_precision must be minute or second")
    coverage = _check_intervals(manifest["observation_intervals"], "observation_intervals")
    gaps = _check_intervals(manifest["known_gaps"], "known_gaps")
    if coverage and any(not any(a <= start < end <= b for a, b in coverage) for start, end in gaps):
        raise ManifestError("Known gaps must lie within a declared observation interval")
    sources = manifest["source_files"]
    if not isinstance(sources, list) or len(sources) != 1:
        raise ManifestError("Version 1 supports exactly one transaction CSV per manifest")
    source = sources[0]
    if not isinstance(source, dict) or set(source) != SOURCE_FIELDS:
        raise ManifestError("Invalid source-file metadata")
    relative_path = _required_text(source["relative_path"], "relative_path")
    relative = PurePosixPath(relative_path)
    if (
        relative.is_absolute() or ".." in relative.parts or "\\" in relative_path
        or str(relative) != relative_path or relative_path == "."
    ):
        raise ManifestError("Source path must be canonical and relative")
    if not isinstance(source["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
        raise ManifestError("Source sha256 must be 64 lowercase hexadecimal characters")
    if type(source["byte_count"]) is not int or source["byte_count"] <= 0:
        raise ManifestError("Source byte_count must be a positive integer")
    if source["header"] != list(IBM_HEADER):
        raise ManifestError("Manifest header does not match the IBM positional contract")
    if manifest["dataset_id"] != _dataset_id(manifest):
        raise ManifestError("dataset_id does not match source metadata and interpretation policy")
    return manifest


def create_manifest(
    source_path: Path,
    raw_root: Path,
    *,
    variant: str,
    acquired_at: str,
    timezone_policy: str,
    timestamp_precision: str,
    source_terms: str,
    source_url: str = SOURCE_URL,
    observation_intervals: list[dict[str, str]] | None = None,
    known_gaps: list[dict[str, str]] | None = None,
    normalization_version: str = "1",
) -> dict[str, Any]:
    """Build provenance for one local file; do not infer observation coverage."""
    manifest = {
        "schema_version": "1",
        "variant": variant,
        "synthetic": True,
        "source_url": source_url,
        "acquired_at": acquired_at,
        "source_terms": source_terms,
        "timezone_policy": timezone_policy,
        "timestamp_precision": timestamp_precision,
        "normalization_version": normalization_version,
        "observation_intervals": observation_intervals or [],
        "known_gaps": known_gaps or [],
        "source_files": [inspect_source(source_path, raw_root)],
    }
    manifest["dataset_id"] = _dataset_id(manifest)
    return validate_manifest(manifest)


def write_manifest(manifest: dict[str, Any], output_path: Path, raw_root: Path) -> Path:
    """Atomically publish a new manifest without overwriting an existing artifact."""
    validate_manifest(manifest)
    root = Path(raw_root).resolve(strict=True)
    output = Path(output_path)
    parent = output.parent.resolve(strict=True)
    if not parent.is_relative_to(root):
        raise ManifestError("Manifest output must remain within the raw directory")
    output = parent / output.name
    if output.suffix != ".json":
        raise ManifestError("Manifest output must use .json")
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".manifest-", dir=parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # link is exclusive: it fails if the destination, even a symlink, exists.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return output


def load_manifest(path: Path) -> dict[str, Any]:
    """Read a strict JSON manifest; reject duplicate keys and non-finite values."""
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ManifestError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ManifestError(f"Non-finite JSON value: {value}")

    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ManifestError("Manifest is not valid UTF-8 JSON") from error
    return validate_manifest(data)


def verify_manifest(manifest_path: Path, raw_root: Path) -> dict[str, Any]:
    """Recompute every recorded source hash/header; return verified metadata."""
    manifest = load_manifest(manifest_path)
    for expected in manifest["source_files"]:
        source = _source_path(raw_root, expected["relative_path"])
        observed = inspect_source(source, raw_root)
        if observed != expected:
            raise ManifestError(f"Source integrity mismatch: {expected['relative_path']}")
    return manifest
