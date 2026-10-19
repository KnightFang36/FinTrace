"""Transactional versioned case records; domain actions live in cases.service."""
import json
from pathlib import Path
from fintrace.contracts import canonical_json
from fintrace.storage.alert_store import AlertStore


class CaseStore(AlertStore):
    def __init__(self, path):
        location = Path(path).absolute()
        if any(p.is_symlink() for p in (location, *location.parents)) or {'raw', 'evaluation'} & set(location.resolve().parts):
            raise ValueError('Use a case store outside raw/evaluation, without symbolic links')
        super().__init__(path)
        self.connection.execute('CREATE TABLE IF NOT EXISTS ft_case_schema(version INTEGER PRIMARY KEY)')
        versions = self.connection.execute('SELECT version FROM ft_case_schema').fetchall()
        if versions and versions != [(1,)]:
            self.close()
            raise ValueError('Unsupported case schema version')
        self.connection.execute('INSERT INTO ft_case_schema VALUES (1) ON CONFLICT DO NOTHING')
        self.connection.execute('CREATE TABLE IF NOT EXISTS ft_cases(id VARCHAR PRIMARY KEY, version INTEGER NOT NULL, payload VARCHAR NOT NULL)')
        self.connection.execute('CREATE TABLE IF NOT EXISTS ft_case_versions(case_id VARCHAR, version INTEGER, payload VARCHAR NOT NULL, PRIMARY KEY(case_id,version))')
        self.connection.execute('CREATE TABLE IF NOT EXISTS ft_case_events(id VARCHAR PRIMARY KEY, case_id VARCHAR, version INTEGER, payload VARCHAR NOT NULL, UNIQUE(case_id,version))')
        self.connection.execute('CREATE TABLE IF NOT EXISTS ft_case_requests(id VARCHAR PRIMARY KEY, request_hash VARCHAR NOT NULL, payload VARCHAR NOT NULL)')

    def get_case(self, case_id):
        row = self.connection.execute('SELECT payload FROM ft_cases WHERE id=?', [case_id]).fetchone()
        if row is None:
            raise ValueError('Unknown case')
        return json.loads(row[0])

    def save_case(self, case, event, expected_version):
        if expected_version == 0:
            self.connection.execute('INSERT INTO ft_cases VALUES (?,?,?)', [case['case_id'], 1, canonical_json(case)])
        else:
            changed = self.connection.execute('UPDATE ft_cases SET version=?,payload=? WHERE id=? AND version=? RETURNING id',
                [case['version'], canonical_json(case), case['case_id'], expected_version]).fetchone()
            if changed is None:
                raise ValueError('Stale case version')
        self.connection.execute('INSERT INTO ft_case_versions VALUES (?,?,?)', [case['case_id'], case['version'], canonical_json(case)])
        self.connection.execute('INSERT INTO ft_case_events VALUES (?,?,?,?)', [event['event_id'], case['case_id'], case['version'], canonical_json(event)])


def read_cases(database, case_id=None, *, version=None):
    """Read without creating a database or schema; bounded current catalog/history."""
    from fintrace.investigations.dashboard import _connect
    if not Path(database).is_file():
        if case_id:
            raise ValueError('Unknown case/version')
        return {'items': [], 'truncated': False}
    with _connect(database) as connection:
        tables = {row[0] for row in connection.execute('SHOW TABLES').fetchall()}
        if 'ft_cases' not in tables:
            if case_id:
                raise ValueError('Unknown case')
            return {'items': [], 'truncated': False}
        if case_id is None:
            rows = connection.execute("SELECT id,version,json_extract_string(payload,'$.title'),json_extract_string(payload,'$.state'),json_extract_string(payload,'$.assignee'),json_extract_string(payload,'$.updated_at') FROM ft_cases ORDER BY id LIMIT 201").fetchall()
            fields = ['case_id', 'version', 'title', 'state', 'assignee', 'updated_at']
            return {'items': [dict(zip(fields, row)) for row in rows[:200]], 'truncated': len(rows) > 200}
        if version is None:
            row = connection.execute('SELECT payload FROM ft_cases WHERE id=?', [case_id]).fetchone()
        else:
            row = connection.execute('SELECT payload FROM ft_case_versions WHERE case_id=? AND version=?', [case_id, version]).fetchone()
        if row is None:
            raise ValueError('Unknown case/version')
        case = json.loads(row[0])
        events = connection.execute('SELECT payload FROM ft_case_events WHERE case_id=? AND version<=? ORDER BY version LIMIT 1001',
                                    [case_id, case['version']]).fetchall()
        from fintrace.contracts import content_id
        if not events or json.loads(events[-1][0])['case_hash'] != content_id(case):
            raise ValueError('Case version integrity mismatch')
        return {'case': case, 'events': [json.loads(row[0]) for row in events[:1000]], 'truncated': len(events) > 1000}
