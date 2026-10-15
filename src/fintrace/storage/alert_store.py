"""Local transactional alert persistence with immutable evidence and append-only audit."""
from pathlib import Path
import json

from fintrace.alerts.engine import build_alerts, transition_alert
from fintrace.contracts import canonical_json


class AlertStore:
    def __init__(self, path):
        import duckdb

        path = Path(path)
        if path.suffix != ".duckdb" or path.is_symlink() or {"raw", "evaluation"} & set(path.parts):
            raise ValueError("Use a local .duckdb alert store outside raw/evaluation data")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(str(path))
        self.connection.execute("CREATE TABLE IF NOT EXISTS ft_alert_schema(version INTEGER PRIMARY KEY)")
        versions = self.connection.execute("SELECT version FROM ft_alert_schema").fetchall()
        if versions and versions != [(1,)]:
            self.close()
            raise ValueError("Unsupported alert store schema version")
        self.connection.execute("INSERT INTO ft_alert_schema VALUES (1) ON CONFLICT DO NOTHING")
        for table in ("ft_findings", "ft_priority_runs", "ft_account_priorities"):
            self.connection.execute(f"CREATE TABLE IF NOT EXISTS {table}(id VARCHAR PRIMARY KEY, payload VARCHAR NOT NULL)")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS ft_alerts(
            id VARCHAR PRIMARY KEY, deduplication_key VARCHAR UNIQUE NOT NULL,
            version INTEGER NOT NULL, payload VARCHAR NOT NULL)""")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS ft_alert_events(
            id VARCHAR PRIMARY KEY, alert_id VARCHAR NOT NULL, version INTEGER NOT NULL,
            payload VARCHAR NOT NULL, UNIQUE(alert_id, version))""")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.connection.close()

    def list_alerts(self):
        return [json.loads(row[0]) for row in self.connection.execute("SELECT payload FROM ft_alerts ORDER BY id").fetchall()]

    def events(self, alert_id):
        return [json.loads(row[0]) for row in self.connection.execute(
            "SELECT payload FROM ft_alert_events WHERE alert_id=? ORDER BY version", [alert_id],
        ).fetchall()]

    def evidence(self, finding_id):
        row = self.connection.execute("SELECT payload FROM ft_findings WHERE id=?", [finding_id]).fetchone()
        if row is None:
            raise ValueError("Unknown finding")
        return json.loads(row[0])

    def priority(self, priority_id):
        row = self.connection.execute("SELECT payload FROM ft_account_priorities WHERE id=?", [priority_id]).fetchone()
        if row is None:
            raise ValueError("Unknown priority")
        return json.loads(row[0])

    def _immutable(self, table, identifier, value):
        # Table identifiers are internal constants, never user input.
        if table not in {"ft_findings", "ft_priority_runs", "ft_account_priorities"}:
            raise ValueError("Unknown evidence table")
        payload = canonical_json(value)
        old = self.connection.execute(f"SELECT payload FROM {table} WHERE id=?", [identifier]).fetchone()
        if old is not None and old[0] != payload:
            raise ValueError("Immutable evidence ID conflict")
        if old is None:
            self.connection.execute(f"INSERT INTO {table} VALUES (?,?)", [identifier, payload])

    def _save(self, alert, event):
        previous = self.connection.execute("SELECT version FROM ft_alerts WHERE id=?", [alert["alert_id"]]).fetchone()
        if (previous is None and alert["version"] != 1) or (previous and previous[0] != alert["version"] - 1):
            raise ValueError("Stale alert version")
        if previous is None:
            self.connection.execute("INSERT INTO ft_alerts VALUES (?,?,?,?)",
                                    [alert["alert_id"], alert["deduplication_key"], alert["version"], canonical_json(alert)])
        else:
            self.connection.execute("UPDATE ft_alerts SET version=?,payload=? WHERE id=? AND version=?",
                                    [alert["version"], canonical_json(alert), alert["alert_id"], previous[0]])
        self.connection.execute("INSERT INTO ft_alert_events VALUES (?,?,?,?)",
                                [event["event_id"], alert["alert_id"], alert["version"], canonical_json(event)])

    def import_analysis(self, findings, priorities, alert_policy, *, actor, at):
        from fintrace.scoring.priority import unique_findings, validate_priority_snapshot

        findings = unique_findings(findings)
        validate_priority_snapshot(priorities)
        self.connection.execute("BEGIN TRANSACTION")
        try:
            changes = build_alerts(findings, priorities, self.list_alerts(), alert_policy, actor=actor, at=at)
            for finding in findings:
                self._immutable("ft_findings", finding.finding_id, finding)
            self._immutable("ft_priority_runs", priorities["snapshot_id"], priorities)
            for priority in priorities["accounts"]:
                self._immutable("ft_account_priorities", priority["priority_id"], priority)
            for alert, event in zip(changes["alerts"], changes["events"]):
                self._save(alert, event)
            self.connection.execute("COMMIT")
            return changes
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def transition(self, alert_id, new_state, *, actor, at, reason, expected_version, reopen=False):
        self.connection.execute("BEGIN TRANSACTION")
        try:
            row = self.connection.execute("SELECT payload FROM ft_alerts WHERE id=?", [alert_id]).fetchone()
            if row is None:
                raise ValueError("Unknown alert")
            alert, event = transition_alert(json.loads(row[0]), new_state, actor=actor, at=at, reason=reason,
                                            expected_version=expected_version, reopen=reopen)
            self._save(alert, event)
            self.connection.execute("COMMIT")
            return alert
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
