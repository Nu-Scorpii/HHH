"""Host-only full SQLite backups. Never exposed as a Discord command."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import uuid

EXPECTED = {'campaigns','receipts','history','rig_rules','rig_audit','private_settings'}


def readonly(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f'Database does not exist: {path}')
    return sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)


def validate(path):
    with closing(readonly(path)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity check failed.')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not EXPECTED <= tables:
            raise ValueError('This is not a complete UA Hero College database.')
        for guild, payload in db.execute('SELECT guild,state FROM campaigns'):
            state = json.loads(payload)
            if not str(guild).isdecimal() or not isinstance(state, dict) or state.get('schema') != 1 or not isinstance(state.get('characters'),dict):
                raise ValueError('Unsupported or invalid campaign data.')


def create(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.exists():
        raise ValueError('Choose a new backup filename; existing files are never overwritten.')
    validate(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name+'.tmp-'+uuid.uuid4().hex)
    try:
        with closing(readonly(source)) as src, closing(sqlite3.connect(temporary)) as dst:
            src.backup(dst)
            dst.execute('PRAGMA journal_mode=DELETE')
        validate(temporary)
        # Atomic, exclusive installation also protects against concurrent backups.
        os.link(temporary,destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def restore(source, destination, *, bot_stopped=False):
    if not bot_stopped:
        raise ValueError('Stop every bot process first, then pass --bot-stopped.')
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError('Backup and destination must be different files.')
    validate(source)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    previous = None
    if destination.exists():
        snapshot = destination.with_name(destination.name+'.before-restore-'+stamp)
        # Even a read-only SQLite connection can rebuild its shared-memory
        # journal. Preserve original bytes before attempting validation.
        raw_snapshot = snapshot.with_name(snapshot.name+'.corrupt')
        raw_snapshot.mkdir()
        for suffix in ['', '-wal', '-shm']:
            old = Path(str(destination)+suffix)
            if old.exists():
                shutil.copy2(old, raw_snapshot/old.name)
        try:
            previous = create(destination,snapshot)
        except (ValueError, sqlite3.Error):
            # A verified backup must also be able to replace a corrupt database.
            previous = raw_snapshot
        else:
            shutil.rmtree(raw_snapshot)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary = destination.with_name(destination.name+'.restore-'+uuid.uuid4().hex)
    try:
        create(source,temporary)
        # With all bot processes stopped, old journals cannot apply to restored data.
        for suffix in ['-wal','-shm']:
            Path(str(destination)+suffix).unlink(missing_ok=True)
        os.replace(temporary,destination)
    finally:
        temporary.unlink(missing_ok=True)
    return previous


def main():
    parser = argparse.ArgumentParser(description='Full UA database backup and offline restore')
    sub = parser.add_subparsers(dest='action',required=True)
    make = sub.add_parser('create',help='Make a consistent backup, including private creator settings')
    make.add_argument('--db',required=True)
    make.add_argument('--out',required=True)
    recover = sub.add_parser('restore',help='Restore while the bot is stopped, preserving the previous database')
    recover.add_argument('--backup',required=True)
    recover.add_argument('--db',required=True)
    recover.add_argument('--bot-stopped',action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'create':
            print('Created full backup:',create(args.db,args.out))
        else:
            previous = restore(args.backup,args.db,bot_stopped=args.bot_stopped)
            print('Restored database:',Path(args.db).resolve())
            if previous:
                print('Previous database preserved:',previous)
    except (ValueError,sqlite3.Error,OSError,json.JSONDecodeError) as exc:
        parser.exit(1,f'Backup operation failed: {exc}\n')


if __name__ == '__main__':
    main()
