import asyncio
import sqlite3
from pathlib import Path
import pytest
from backup import create, restore, validate
from conftest import World
from ua_bot.__main__ import database_path, run


def test_online_full_backup_restore_and_previous_snapshot(tmp_path):
    database, backup = tmp_path/'game.sqlite3', tmp_path/'full.sqlite3'
    w = World(database)
    w.create()
    w.game.private.handle(1,'!Rigger next 2 max',is_dm=True,guild_ids=[100])
    original = w.state
    create(database,backup)  # The source connection is still open in WAL mode.
    w.call('milestone',reason='Later change')
    changed = w.state
    w.store.close()
    previous = restore(backup,database,bot_stopped=True)
    validate(database)
    r = World(database)
    assert r.state == original
    assert r.store.db.execute('SELECT remaining FROM rig_rules').fetchone()[0] == 1
    r.store.close()
    old = World(previous)
    assert old.state == changed
    old.store.close()


def test_backup_rejects_overwrites_incomplete_source_and_active_restore(tmp_path):
    database, backup = tmp_path/'game.sqlite3', tmp_path/'full.sqlite3'
    w = World(database)
    create(database,backup)
    with pytest.raises(ValueError):
        create(database,backup)
    with pytest.raises(ValueError):
        restore(backup,database)
    other = tmp_path/'other.sqlite3'
    sqlite3.connect(other).close()
    with pytest.raises(ValueError):
        create(other,tmp_path/'bad.sqlite3')
    w.store.close()


@pytest.mark.parametrize('mount,path', [(None,'/data/ua.sqlite3'),('/data','data/ua.sqlite3'),('/data','/tmp/ua.sqlite3')])
def test_railway_startup_refuses_ephemeral_database(monkeypatch,mount,path):
    monkeypatch.setenv('DISCORD_TOKEN','offline-test-placeholder')
    monkeypatch.setenv('BOT_OWNER_ID','1')
    monkeypatch.setenv('RAILWAY_ENVIRONMENT_ID','test')
    monkeypatch.setenv('BOT_DB_PATH',path)
    if mount is None:
        monkeypatch.delenv('RAILWAY_VOLUME_MOUNT_PATH',raising=False)
    else:
        monkeypatch.setenv('RAILWAY_VOLUME_MOUNT_PATH',mount)
    with pytest.raises(SystemExit,match='persistent volume'):
        asyncio.run(run())


def test_railway_database_defaults_to_attached_volume_and_honors_valid_override(tmp_path):
    volume=tmp_path/'volume'
    volume.mkdir()
    env={'RAILWAY_ENVIRONMENT_ID':'test','RAILWAY_VOLUME_MOUNT_PATH':str(volume)}
    assert database_path(env)==str(volume/'ua.sqlite3')
    env['BOT_DB_PATH']=str(volume/'campaign'/'saved.sqlite3')
    assert database_path(env)==env['BOT_DB_PATH']
    assert database_path({})=='data/ua.sqlite3'
    assert database_path({'BOT_DB_PATH':'local/save.sqlite3'})=='local/save.sqlite3'


@pytest.mark.parametrize('marker',['RAILWAY_ENVIRONMENT_ID','RAILWAY_PROJECT_ID','RAILWAY_SERVICE_ID'])
def test_all_railway_environment_markers_require_real_volume_configuration(marker):
    with pytest.raises(SystemExit,match='persistent volume'):
        database_path({marker:'test'})


def test_railway_rejects_volume_root_traversal_and_symlink_escape(tmp_path):
    volume=tmp_path/'volume';volume.mkdir()
    outside=tmp_path/'outside';outside.mkdir()
    (volume/'link').symlink_to(outside,target_is_directory=True)
    env={'RAILWAY_ENVIRONMENT_ID':'test','RAILWAY_VOLUME_MOUNT_PATH':str(volume)}
    for target in [volume,volume/'..'/'outside'/'ua.sqlite3',volume/'link'/'ua.sqlite3']:
        env['BOT_DB_PATH']=str(target)
        with pytest.raises(SystemExit,match='persistent volume'):
            database_path(env)


def test_restore_valid_backup_over_corrupt_database_preserves_raw_files(tmp_path):
    source, backup, destination = tmp_path/'source.sqlite3', tmp_path/'backup.sqlite3', tmp_path/'broken.sqlite3'
    w = World(source)
    w.create()
    original = w.state
    create(source, backup)
    w.store.close()
    old = {suffix: b'corrupt original '+suffix.encode() for suffix in ['', '-wal', '-shm']}
    for suffix, payload in old.items():
        Path(str(destination)+suffix).write_bytes(payload)
    previous = restore(backup, destination, bot_stopped=True)
    assert previous.is_dir()
    for suffix, payload in old.items():
        assert (previous/(destination.name+suffix)).read_bytes() == payload
    validate(destination)
    restored = World(destination)
    assert restored.state == original
    restored.store.close()


def test_invalid_restore_source_never_touches_current_database(tmp_path):
    source, destination = tmp_path/'bad.sqlite3', tmp_path/'current.sqlite3'
    source.write_bytes(b'not a database')
    destination.write_bytes(b'original database bytes')
    with pytest.raises(sqlite3.Error):
        restore(source, destination, bot_stopped=True)
    assert destination.read_bytes() == b'original database bytes'
    assert not list(tmp_path.glob('*.before-restore-*'))


def test_backup_validation_rejects_wrong_json_shape_with_friendly_error(tmp_path):
    path = tmp_path/'invalid-payload.sqlite3'
    w = World(path)
    w.store.db.execute('INSERT INTO campaigns VALUES (?,?)', ('100', '[]'))
    w.store.close()
    with pytest.raises(ValueError, match='campaign'):
        validate(path)


def test_startup_rejects_zero_server_id_before_connecting(monkeypatch, tmp_path):
    monkeypatch.setenv('DISCORD_TOKEN', 'offline-test-placeholder')
    monkeypatch.setenv('BOT_OWNER_ID', '1')
    monkeypatch.setenv('DISCORD_GUILD_ID', '0')
    monkeypatch.setenv('BOT_DB_PATH', str(tmp_path/'unused.sqlite3'))
    for name in ['RAILWAY_ENVIRONMENT_ID', 'RAILWAY_PROJECT_ID', 'RAILWAY_SERVICE_ID']:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(SystemExit, match='DISCORD_GUILD_ID'):
        asyncio.run(run())
    assert not (tmp_path/'unused.sqlite3').exists()
