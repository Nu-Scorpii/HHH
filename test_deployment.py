"""Run the real deployable bundle from an isolated four-file upload."""

import os
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tomllib
import zipfile

import pytest
from backup import validate
from build_release import build
from conftest import World

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def upload(tmp_path):
    for name in ['Dockerfile', 'requirements.txt', 'railway.toml']:
        shutil.copy2(PROJECT/name, tmp_path/name)
    build(PROJECT, tmp_path/'bot.pyz')
    return tmp_path


def run_bundle(upload, *args):
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    environment.pop('PYTHONPATH', None)
    return subprocess.run([sys.executable, str(upload/'bot.pyz'), *args], cwd=upload,
                          env=environment, capture_output=True, text=True, timeout=30)


def test_four_flat_files_supply_every_docker_copy_and_offline_startup(upload):
    assert {p.name for p in upload.iterdir()} == {'Dockerfile', 'requirements.txt', 'railway.toml', 'bot.pyz'}
    for line in (upload/'Dockerfile').read_text().splitlines():
        if line.startswith('COPY '):
            for source in shlex.split(line)[1:-1]:
                assert (upload/source).is_file(), f'Missing Docker build input: {source}'
    config = tomllib.loads((upload/'railway.toml').read_text())
    assert config['build']['builder'] == 'DOCKERFILE'
    command = shlex.split(config['deploy']['startCommand'])
    # New Railway services need no legacy TOML reader: Docker itself starts
    # the same bundle when no dashboard start override is present.
    docker_command = next(line[4:].strip() for line in (upload/'Dockerfile').read_text().splitlines() if line.startswith('CMD '))
    assert json.loads(docker_command) == command
    result = run_bundle(upload, '--check')
    assert command == ['python', 'bot.pyz']
    assert result.returncode == 0, result.stderr
    assert '88 slash commands across 20 root commands' in result.stdout
    assert 'No network login performed' in result.stdout
    assert not (upload/'data').exists()


def test_bundle_contains_current_sources_and_handbook_but_no_private_documents(upload):
    with zipfile.ZipFile(upload/'bot.pyz') as bundle:
        sources = sorted((PROJECT/'ua_bot').glob('*.py')) + [PROJECT/'backup.py']
        expected = {'__main__.py', 'ua_bot/PLAYER_HANDBOOK.md'}
        for source in sources:
            name = source.relative_to(PROJECT).as_posix()
            expected.add(name)
            assert bundle.read(name) == source.read_bytes()
        assert set(bundle.namelist()) == expected
        assert bundle.read('ua_bot/PLAYER_HANDBOOK.md') == (PROJECT/'docs'/'PLAYER_HANDBOOK.md').read_bytes()


def test_bundled_backup_cli_makes_a_complete_online_backup(upload):
    w = World(upload/'game.sqlite3')
    w.create()
    w.game.private.handle(1, '!Rigger next 2 max', is_dm=True, guild_ids=[100])
    original = w.state
    result = run_bundle(upload, 'backup', 'create', '--db', 'game.sqlite3', '--out', 'saved.sqlite3')
    assert result.returncode == 0, result.stderr
    validate(upload/'saved.sqlite3')
    saved = World(upload/'saved.sqlite3')
    assert saved.state == original
    assert saved.store.db.execute('SELECT remaining FROM rig_rules').fetchone()[0] == 1
    saved.store.close()
    w.store.close()
