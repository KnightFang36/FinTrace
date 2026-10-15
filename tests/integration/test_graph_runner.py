"""Verified ingest-to-graph evidence and reproducible bounded visualization."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fintrace.graph.runner import run_graph_snapshot
from fintrace.ingestion.ibm import ingest_ibm
from fintrace.ingestion.manifest import IBM_HEADER, create_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", "/tmp/fintrace-matplotlib-tests")


@pytest.fixture
def prepared(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "source.csv"
    source.write_text(",".join(IBM_HEADER) + "\n" +
                      "2022/09/01 00:01,1,A,1,B,10.00,USD,10.00,USD,ACH,0\n" +
                      "2022/09/01 00:02,1,B,1,C,10.00,USD,10.00,USD,ACH,1\n" +
                      "2022/09/01 00:03,1,C,1,A,10.00,USD,10.00,USD,ACH,1\n")
    manifest = create_manifest(source, raw, variant="HI-Small", acquired_at=None, timezone_policy="UTC",
                               timestamp_precision="minute", source_terms="Handcrafted fixture")
    ingest_ibm(write_manifest(manifest, raw / "manifest.json", raw), raw, tmp_path / "processed")
    evaluation = tmp_path / "processed/evaluation" / manifest["dataset_id"] / "labels.parquet"
    evaluation.write_bytes(b"Corrupt evaluation must never be read by graph analysis")
    return tmp_path / "processed/datasets" / manifest["dataset_id"] / "transactions.parquet"


def test_graph_snapshot_evidence_png_and_verified_reuse(prepared, tmp_path):
    result = run_graph_snapshot(prepared, ROOT / "config/graph.toml", "2022-09-01T03:00:00Z", tmp_path / "runs")
    assert result["findings_by_rule"] == {"circular_flow": 1}
    directory = Path(result["output_directory"])
    evidence = json.loads((directory / "graph.json").read_text())
    assert len(evidence["findings"][0]["transaction_ids"]) == 3
    assert evidence["source_context"]["timestamp_precision"] == "minute"
    assert (directory / "network.png").read_bytes().startswith(b"\x89PNG")
    assert "is_laundering" not in json.dumps(evidence)
    again = run_graph_snapshot(prepared, ROOT / "config/graph.toml", "2022-09-01T03:00:00Z", tmp_path / "runs")
    assert again["status"] == "reused"
    (directory / "network.png").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        run_graph_snapshot(prepared, ROOT / "config/graph.toml", "2022-09-01T03:00:00Z", tmp_path / "runs")


def test_cli_declares_visualization_truncation(prepared, tmp_path):
    policy = tmp_path / "graph.toml"
    policy.write_text((ROOT / "config/graph.toml").read_text().replace("max_display_nodes = 100", "max_display_nodes = 2"))
    command = [sys.executable, str(ROOT / "scripts/run_graphs.py"), str(prepared), "--cutoff", "2022-09-01T03:00:00Z",
               "--policy", str(policy), "--output-root", str(tmp_path / "runs")]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["visualization"]["status"] == "truncated"
    assert output["visualization"]["nodes_shown"] == 2
    result = subprocess.run(command[:1] + ["-S"] + command[1:], capture_output=True, text=True)
    assert result.returncode == 2
    assert "config/data-requirements.txt" in result.stderr
    assert "Traceback" not in result.stderr


def test_bad_source_rejected_before_graph_publication(prepared, tmp_path):
    with prepared.open("ab") as handle:
        handle.write(b"changed")
    with pytest.raises(ValueError, match="integrity"):
        run_graph_snapshot(prepared, ROOT / "config/graph.toml", "2022-09-01T03:00:00Z", tmp_path / "runs")
    assert not (tmp_path / "runs").exists()
