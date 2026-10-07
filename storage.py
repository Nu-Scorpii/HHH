"""Transactional SQLite persistence. Private dice controls have separate tables."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def fresh_campaign():
    return {
        "schema": 1,
        "settings": {"gm_role_id": None, "timezone": "America/New_York", "reset_weekday": 0, "reset_hour": 0},
        "milestones": 0, "characters": {}, "dice": {}, "faq": {}, "scene": 0,
        "session": None, "session_log": [], "mission": None,
        "battle": None, "spar": None, "pending": None,
    }


class Store:
    def __init__(self, path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS campaigns (guild TEXT PRIMARY KEY, state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS receipts (request TEXT PRIMARY KEY, guild TEXT NOT NULL, result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY, guild TEXT NOT NULL, actor TEXT NOT NULL,
                operation TEXT NOT NULL, before_state TEXT NOT NULL, created TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS history_guild ON history(guild, id);
            CREATE TABLE IF NOT EXISTS rig_rules (
                id INTEGER PRIMARY KEY, guild TEXT NOT NULL, target TEXT NOT NULL,
                outcome TEXT NOT NULL, scope TEXT NOT NULL, remaining INTEGER NOT NULL,
                expires REAL NOT NULL, creator TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS rig_audit (
                id INTEGER PRIMARY KEY, guild TEXT NOT NULL, target TEXT NOT NULL,
                rule_id INTEGER NOT NULL, natural TEXT NOT NULL, final TEXT NOT NULL, created TEXT NOT NULL);
        """)

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield self.db
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def load(self, guild):
        row = self.db.execute("SELECT state FROM campaigns WHERE guild=?", (str(guild),)).fetchone()
        return json.loads(row[0]) if row else fresh_campaign()

    def save(self, guild, state):
        self.db.execute("INSERT INTO campaigns VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET state=excluded.state",
                        (str(guild), json.dumps(state, ensure_ascii=False)))

    def close(self):
        self.db.close()
