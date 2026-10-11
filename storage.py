"""Small atomic store. Older campaign tables are left untouched and never loaded."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from .controls import empty_setting, MAX_VALUE
from .errors import require

CACHE_LIMIT = 1000


class Store:
    def __init__(self, path='data/ua.sqlite3'):
        if str(path) != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), isolation_level=None, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS dice_settings_v3 (owner TEXT PRIMARY KEY, state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS dice_receipts_v3 (
                kind TEXT NOT NULL, request TEXT NOT NULL, signature TEXT NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY(kind, request));
        ''')

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def setting(self, owner):
        row = self.db.execute('SELECT state FROM dice_settings_v3 WHERE owner=?', (str(owner),)).fetchone()
        if not row:
            return empty_setting()
        try:
            state = json.loads(row['state'])
            mode, value, target = state['mode'], state['value'], state['target']
            assert mode in ('off', 'good', 'bad', 'force', 'shift', 'face')
            assert target is None or isinstance(target, str) and target.isdecimal() and 0 < int(target) < 2**64
            if mode in ('force', 'shift'):
                assert type(value) is int and abs(value) <= MAX_VALUE
            elif mode == 'face':
                assert isinstance(value, str) and 1 <= len(value) <= 40
            else:
                assert value is None
            assert state.get('last') is None or isinstance(state['last'], str) and len(state['last']) <= 1000
            return {**empty_setting(), **{key: state[key] for key in empty_setting() if key in state}}
        except (ValueError, TypeError, KeyError, AssertionError):
            return empty_setting()

    def save_setting(self, owner, setting):
        self.db.execute('INSERT INTO dice_settings_v3 VALUES (?,?) ON CONFLICT(owner) DO UPDATE SET state=excluded.state',
                        (str(owner), json.dumps(setting, ensure_ascii=False)))

    def receipt(self, kind, request, signature):
        if request is None:
            return None
        row = self.db.execute('SELECT signature,result FROM dice_receipts_v3 WHERE kind=? AND request=?', (kind, str(request))).fetchone()
        if not row:
            return None
        require(row['signature'] == signature, 'This request ID was already used for a different command. Run a fresh /roll.')
        return json.loads(row['result'])

    def remember(self, kind, request, signature, result):
        if request is None:
            return
        self.db.execute('INSERT INTO dice_receipts_v3 VALUES (?,?,?,?)',
                        (kind, str(request), signature, json.dumps(result, ensure_ascii=False)))
        self.db.execute('DELETE FROM dice_receipts_v3 WHERE rowid NOT IN (SELECT rowid FROM dice_receipts_v3 ORDER BY rowid DESC LIMIT ?)', (CACHE_LIMIT,))

    def close(self):
        self.db.close()
