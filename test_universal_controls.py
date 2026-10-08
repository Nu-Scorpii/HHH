"""Universal creator controls: legal arithmetic, probability, persistence and privacy."""

import asyncio
from datetime import timedelta
import itertools
import json
import random
from unittest.mock import AsyncMock

import pytest

from backup import create, restore
from conftest import Fixed, World
from ua_bot.client import HeroBot
from ua_bot.commands import SPECS, help_text
from ua_bot.core import Actor
from ua_bot.display import messages
from ua_bot.dice import parse, roll_expression
from ua_bot.rigging_math import expression_result, variables
from ua_bot.rules import GameError


class Draws:
    def __init__(self, *values):
        self.values = iter(values)
        self.count = 0

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        self.count += 1
        return value

    def choice(self, values):
        value = next(self.values)
        assert value in values
        self.count += 1
        return value


def dm(world, command):
    return world.game.private.handle(1, '!Rigger ' + command, is_dm=True, guild_ids=())


def raw(world, expression='d20', *, guild=100, user=2, rng=None, custom=None, keep='all', bonus=0):
    with world.store.transaction():
        return world.game.private.expression(guild, user, expression, custom or {}, keep, rng or Fixed(), bonus=bonus)


def tracked(world, *, guild=100, user=2, sides=10, edge=False, pressure=False, rng=None, scope='check', stat='power'):
    with world.store.transaction():
        return world.game.private.stat(guild, user, scope, stat, sides, edge, pressure, rng or Fixed())


def remaining(world, mode):
    return [row[0] for row in world.store.db.execute('SELECT remaining FROM rig_rules WHERE mode=? ORDER BY id', (mode,))]


def consistent(result, expression, custom=None):
    terms = parse(expression, custom or {})
    dice = variables(terms)
    faces = [value for group in result['groups'] if 'die' in group for value in group['rolls']]
    assert len(faces) == len(dice)
    assert all(die.contains(value) for value, (die, _) in zip(faces, dice))
    total = result['bonus'] + sum(g.get('modifier', 0) for g in result['groups'])
    for group in result['groups']:
        if 'die' not in group:
            continue
        if result['keep'] == 'all':
            assert group['kept'] is None
            value = sum(group['rolls'])
        else:
            value = (max if result['keep'] == 'high' else min)(group['rolls'])
            assert group['kept'] == value
        total += group['sign'] * value
    assert result['total'] == total


def test_universal_budget_needs_no_server_selection_and_includes_future_servers(world):
    assert 'across all servers' in dm(world, 'force 15 uses:2')
    assert raw(world, guild=200)['total'] == 15
    assert raw(world, guild=999999)['total'] == 15
    assert raw(world, guild=100)['total'] == 5
    assert remaining(world, 'force') == [0]
    assert [r[0] for r in world.store.db.execute('SELECT guild FROM rig_audit')] == ['200', '999999']
    assert world.store.db.execute('SELECT guild FROM rig_rules').fetchone()[0] == '*'
    assert 'server 999999' in dm(world, 'audit')


@pytest.mark.parametrize('expression,bonus,keep,wanted', [
    ('2d20', 0, 'all', 15), ('2d17+1d8-3', 6, 'all', 15),
    ('d4-2d6+9', -2, 'all', -3), ('2d20+3', 4, 'high', 22),
    ('2d20-3', -4, 'low', 1), ('100d1000000000', 0, 'all', 99999999999),
])
def test_force_controls_final_total_with_legal_faces(world, expression, bonus, keep, wanted):
    dm(world, f'force {wanted}')
    result = raw(world, expression, bonus=bonus, keep=keep)
    assert result['total'] == wanted
    consistent(result, expression)
    assert remaining(world, 'force') == [0]


@pytest.mark.parametrize('mode,edge,pressure', [('normal', False, False), ('edge', True, False), ('pressure', False, True), ('normal', True, True)])
def test_forced_stat_preserves_mode_faces_and_kept_result(world, mode, edge, pressure):
    dm(world, 'force 8')
    result = tracked(world, edge=edge, pressure=pressure, rng=Fixed(2))
    assert result['mode'] == mode and result['kept'] == 8
    assert all(1 <= face <= 10 for face in result['rolls'])
    assert len(result['rolls']) == (1 if mode == 'normal' else 2)
    assert (min if mode == 'pressure' else max)(result['rolls']) == 8


@pytest.mark.parametrize('command,wanted', [('force min', -11), ('force max', 2), ('shift -100', -11), ('shift +100', 2)])
def test_signed_pool_limits_and_clamped_shifts(world, command, wanted):
    dm(world, command)
    result = raw(world, 'd4-2d6-1+1', bonus=0)
    assert result['total'] == wanted
    consistent(result, 'd4-2d6-1+1')


def test_shift_changes_pool_total_once_and_visible_bonus_stays_separate(world):
    dm(world, 'shift +3')
    result = world.call('roll', 2, dice='2d20+2', bonus=4)['dice']
    assert result['total'] == 19  # 5 + 5 + 2 + 4 + 3, once per roll.
    assert result['bonus'] == 4 and result['groups'][1] == {'modifier': 2}
    consistent(result, '2d20+2')
    output = '\n'.join(messages({'type': 'dice', 'dice': result, 'roller': 'Hero'}))
    assert all(word not in output.lower() for word in ['rigger', 'override', 'natural', 'shift', 'luck'])


@pytest.mark.parametrize('keep,wanted', [('all', 8), ('high', 7), ('low', -3)])
def test_custom_numeric_force_preserves_allowed_faces(world, keep, wanted):
    custom = {'custom': [-3, 0, 4, 7, 7]}
    dm(world, f'force {wanted}')
    result = raw(world, '2d[custom]', custom=custom, keep=keep)
    assert result['total'] == wanted
    consistent(result, '2d[custom]', custom)


def test_unreachable_force_waits_for_compatible_total(world):
    custom = {'custom': [0, 4, 7]}
    dm(world, 'force 9')
    assert raw(world, '2d[custom]', custom=custom)['total'] == 0
    assert remaining(world, 'force') == [1]
    assert raw(world, 'd20')['total'] == 9
    assert remaining(world, 'force') == [0]


def test_non_greedy_sparse_combinations_and_search_budget(world, monkeypatch):
    custom = {'custom': [0, 4, 7]}
    terms = parse('2d[custom]', custom)
    natural = roll_expression('2d[custom]', custom, Fixed())
    exact = expression_result(natural, terms, 'force', '8')
    assert exact['groups'][0]['rolls'] == [4, 4]
    monkeypatch.setattr('ua_bot.rigging_math.MAX_SEARCH', 0)
    dm(world, 'force 8')
    assert raw(world, '2d[custom]', custom=custom)['total'] == 0
    assert remaining(world, 'force') == [1]
    dm(world, 'clear')
    dm(world, 'shift +8')
    shifted = raw(world, '2d[custom]', custom=custom)
    consistent(shifted, '2d[custom]', custom)
    assert shifted['total'] in {0, 4, 7, 8, 11, 14}


def test_exact_solver_matches_exhaustive_small_custom_dice():
    # Compare to all legal outcomes, rather than mirroring the search implementation.
    custom = {'a': [-3, 0, 4, 7], 'b': [-2, 1, 5]}
    for expression in ['2d[a]+d[b]-2', 'd[a]-2d[b]+3', 'd[a]+d5-1']:
        terms = parse(expression, custom)
        dice = variables(terms)
        fixed = sum(sign * term for sign, term in terms if isinstance(term, int))
        possible = {fixed + sum(sign * face for face, (_, sign) in zip(combo, dice))
                    for combo in itertools.product(*(range(1, die.sides + 1) if die.sides else set(die.faces) for die, _ in dice))}
        natural = roll_expression(expression, custom, Fixed())
        for wanted in range(min(possible) - 1, max(possible) + 2):
            result = expression_result(natural, terms, 'force', str(wanted))
            assert (result is not None) == (wanted in possible), (expression, wanted)
            if result:
                assert result['total'] == wanted
                consistent(result, expression, custom)


@pytest.mark.parametrize('keep,start,delta,wanted', [('all', 7, 3, 14), ('high', 0, 3, 4), ('low', 4, -3, 0)])
def test_sparse_shift_keeps_faces_legal_and_uses_nearest_available(world, keep, start, delta, wanted):
    dm(world, f'shift {delta:+}')
    custom = {'custom': [0, 4, 7]}
    result = raw(world, '2d[custom]', custom=custom, keep=keep, rng=Draws(start, start))
    assert result['total'] == wanted
    consistent(result, '2d[custom]', custom)


@pytest.mark.parametrize('command,start,sides,wanted,consumed', [
    ('shift success', 2, 10, 4, True), ('shift miss', 9, 10, 3, True),
    ('shift big', 5, 10, 8, True), ('shift big', 5, 6, 5, False),
    ('shift up', 2, 6, 4, True), ('shift up', 5, 6, 5, True),
    ('shift down', 8, 10, 7, True), ('shift down', 2, 10, 2, True),
])
def test_stat_outcome_categories_respect_die_limits(world, command, start, sides, wanted, consumed):
    dm(world, command)
    assert tracked(world, sides=sides, rng=Fixed(start))['kept'] == wanted
    assert remaining(world, 'outcome') == [0 if consumed else 1]


def test_raw_outcome_uses_final_total_and_skips_unavailable_grades(world):
    custom = {'custom': [0, 8]}
    dm(world, 'shift up')
    assert raw(world, 'd[custom]', custom=custom)['total'] == 8
    dm(world, 'shift success')
    result = raw(world, 'd20+2', bonus=1, rng=Fixed(15))
    assert result['total'] == 7
    consistent(result, 'd20+2')


@pytest.mark.parametrize('direction,candidates,wanted', [('good', (3, 17), 17), ('bad', (17, 3), 3), ('+3', (4, 9, 20, 7), 20), ('-3', (14, 9, 2, 7), 2)])
def test_luck_biases_numeric_rolls_with_only_ordinary_faces(world, direction, candidates, wanted):
    dm(world, f'luck {direction}')
    rng = Draws(*candidates)
    result = raw(world, rng=rng, guild=200)
    assert result['total'] == wanted and len(result['groups'][0]['rolls']) == 1
    assert rng.count == len(candidates) and remaining(world, 'luck') == [-1]


def test_luck_changes_probability_without_guaranteeing_results(world):
    averages, results = {}, {}
    for direction in ['normal', 'good', 'bad']:
        dm(world, f'luck {direction}')
        rng = random.Random(42)
        with world.store.transaction():
            rolls = [world.game.private.stat(200, 2, 'check', 'power', 10, False, False, rng)['kept'] for _ in range(600)]
        averages[direction] = sum(rolls) / len(rolls)
        results[direction] = set(rolls)
    assert averages['bad'] + 1 < averages['normal'] < averages['good'] - 1
    assert all(values == set(range(1, 11)) for values in results.values())


def test_luck_chooses_complete_signed_pool_by_total(world):
    dm(world, 'luck good uses:1')
    result = raw(world, 'd20-d20', rng=Draws(20, 19, 3, 1))
    assert result['groups'][0]['rolls'] == [3] and result['groups'][1]['rolls'] == [1]
    assert result['total'] == 2 and remaining(world, 'luck') == [0]


@pytest.mark.parametrize('edge,pressure,draws,wanted', [(True,False,(2,4,3,8),8), (False,True,(8,9,7,10),8), (True,True,(2,9),9)])
def test_luck_preserves_stat_edge_pressure_and_cancellation(world, edge, pressure, draws, wanted):
    dm(world, 'luck good')
    result = tracked(world, edge=edge, pressure=pressure, rng=Draws(*draws))
    assert result['kept'] == wanted
    assert (min if pressure and not edge else max)(result['rolls']) == wanted
    assert len(result['rolls']) == (1 if edge == pressure else 2)


def test_text_and_mixed_dice_do_not_consume_numeric_controls(world):
    dm(world, 'luck good uses:1')
    dm(world, 'shift +3')
    rng = Draws('sun')
    assert raw(world, 'd[custom]', custom={'custom': [2, 'sun']}, rng=rng)['total'] is None
    assert rng.count == 1 and remaining(world, 'luck') == [1] and remaining(world, 'shift') == [1]
    dm(world, 'force "heavy rain"')
    result = raw(world, 'd[custom]', custom={'custom': ['sun', 'heavy rain']})
    assert result['groups'][0]['rolls'] == ['heavy rain']
    assert remaining(world, 'luck') == [1] and remaining(world, 'shift') == [1]


def test_exact_force_has_priority_but_luck_then_shift_can_combine(world):
    dm(world, 'luck good uses:2')
    dm(world, 'force 15')
    rng = Draws(2)
    assert raw(world, rng=rng)['total'] == 15 and rng.count == 1
    assert remaining(world, 'luck') == [2]
    dm(world, 'shift +3')
    assert raw(world, rng=Draws(2, 10))['total'] == 13
    assert remaining(world, 'luck') == [1] and remaining(world, 'shift') == [0]
    audit = world.store.db.execute('SELECT natural,final FROM rig_audit ORDER BY id').fetchall()
    assert [(json.loads(r[0])['total'], json.loads(r[1])['total']) for r in audit] == [(2,15), (2,10), (10,13)]


def test_targeted_normal_temporarily_masks_global_luck_across_servers(world):
    dm(world, 'luck good')
    dm(world, 'luck normal <@!2> uses:1')
    assert raw(world, guild=200, rng=Draws(2))['total'] == 2
    assert raw(world, guild=100, rng=Draws(2, 12))['total'] == 12
    dm(world, 'luck bad 3 scope:attack')
    assert tracked(world, user=3, scope='defense', rng=Draws(2,9))['kept'] == 9
    assert tracked(world, user=3, scope='attack', rng=Draws(9,2))['kept'] == 2
    assert 'Player/scoped settings remain' in dm(world, 'luck normal')
    assert tracked(world, user=3, scope='attack', rng=Draws(9,2))['kept'] == 2


def test_target_scope_aliases_and_lasting_controls(world):
    dm(world, 'force 8 target:<@2> scope:power uses:always')
    assert tracked(world, user=3)['kept'] == 5
    assert tracked(world, stat='speed')['kept'] == 5
    assert tracked(world, guild=200)['kept'] == 8
    world.now += timedelta(days=8)
    assert tracked(world, guild=9876)['kept'] == 8
    assert remaining(world, 'force') == [-1]
    dm(world, 'shift -2 me scope:roll count:1 minutes:1')
    assert raw(world, user=2)['total'] == 5
    assert raw(world, user=1)['total'] == 3
    dm(world, 'clear')
    assert dm(world, 'status') == 'No queued rules.'


def test_expiry_boundary_applies_even_to_persistent_luck(world):
    dm(world, 'luck good minutes:1')
    dm(world, 'force 15 uses:always minutes:1')
    world.now += timedelta(seconds=60)
    assert raw(world, rng=Draws(5))['total'] == 5
    assert dm(world, 'status') == 'No queued rules.'


@pytest.mark.parametrize('command', [
    'luck 4', 'luck -4', 'force 1000000000001', 'shift -1000000000001',
    'shift nope', 'outcome 3', 'force 8 uses:0', 'force 8 uses:-1', 'force 8 uses:101',
    'force 8 minutes:0', 'force 8 minutes:1441', 'force 8 scope:unknown',
    'force 8 <@&2>', 'force 8 <@2>garbage', 'force 8 0', 'force 8 18446744073709551616',
    'force 8 2 3', 'force 8 uses:2 count:3', 'force 8 bogus:2', 'clear 9223372036854775808',
])
def test_invalid_controls_are_atomic_and_give_private_error(world, command):
    dm(world, 'luck good')
    assert dm(world, command).startswith('Could not apply')
    assert remaining(world, 'luck') == [-1]
    assert world.store.db.execute('SELECT count(*) FROM rig_rules').fetchone()[0] == 1


def test_repeat_receipt_and_failed_transaction_do_not_double_spend(world, monkeypatch):
    dm(world, 'force 15 uses:2')
    first = world.game.execute(Actor(200,2), 'roll', dice='d20', request_id=12345)
    assert world.game.execute(Actor(200,2), 'roll', dice='d20', request_id=12345) == first
    assert remaining(world, 'force') == [1]
    original = world.game.private.expression
    def fail_after_roll(*args, **kwargs):
        original(*args, **kwargs)
        raise GameError('Test failure after rolling')
    monkeypatch.setattr(world.game.private, 'expression', fail_after_roll)
    with pytest.raises(GameError, match='after rolling'):
        world.call('roll', 2)
    assert remaining(world, 'force') == [1]
    assert world.store.db.execute('SELECT count(*) FROM rig_audit').fetchone()[0] == 1


def test_private_controls_still_feed_tracked_checks_and_plus_ultra(world):
    world.create()
    dm(world, 'shift -3 scope:check')
    result = world.call('check', 2, stat='power', method='Lift rubble')
    assert result['roll']['kept'] == 2
    assert remaining(world, 'shift') == [0]
    world.call('resolve', 2, plus_ultra=True)
    assert world.h()['health'] == 4 and world.h()['plus_used']


@pytest.mark.parametrize('scope', ['attack', 'spar'])
def test_battle_and_spar_use_the_same_universal_roll_controls(world, scope):
    world.create(2)
    world.create(3)
    dm(world, f'force 8 2 scope:{scope}')
    if scope == 'attack':
        world.battle()
        world.call('battle_turn', 2)
        result = world.call('battle_attack', 2, targets='e1', stat='power', method='Ice strike')
        roll = result['roll']
    else:
        world.call('spar_start', 2, opponent=3)
        world.call('spar_join', 3)
        world.call('spar_roll', 2, stat='power', method='Friendly ice strike')
        roll = world.state['spar']['rolls']['2']
    assert roll['kept'] == 8 and remaining(world, 'force') == [0]


def test_old_database_and_backup_migrate_without_losing_campaign_or_queue(tmp_path):
    database, backup, destination = (tmp_path/name for name in ['old.sqlite3', 'backup.sqlite3', 'restored.sqlite3'])
    world = World(database)
    world.create()
    original = world.state
    dm(world, 'next 2 7 3 dice 60')
    world.store.db.execute("UPDATE rig_rules SET guild='100'")
    world.store.db.execute('ALTER TABLE rig_rules DROP COLUMN mode')
    world.store.db.execute("INSERT INTO private_settings VALUES('1','100')")
    original_rule = dict(world.store.db.execute('SELECT * FROM rig_rules').fetchone())
    create(database, backup)
    world.store.close()
    restore(backup, destination, bot_stopped=True)
    for _ in range(2):
        reopened = World(destination)
        assert reopened.state == original
        rule = dict(reopened.store.db.execute('SELECT * FROM rig_rules').fetchone())
        assert rule == dict(original_rule, guild='*', mode='face')
        assert reopened.store.db.execute('SELECT guild FROM private_settings').fetchone()[0] == '100'
        reopened.store.close()
    reopened = World(destination)
    assert raw(reopened, '2d20', guild=200)['total'] == 14  # Legacy per-face behavior survives.
    reopened.store.close()


def test_new_persistent_controls_and_audit_survive_full_backup_and_restart(tmp_path):
    database, backup, destination = (tmp_path/name for name in ['new.sqlite3', 'backup.sqlite3', 'restored.sqlite3'])
    world = World(database)
    dm(world, 'luck good')
    dm(world, 'shift +3 uses:always')
    assert raw(world, guild=200, rng=Draws(2,10))['total'] == 13
    create(database, backup)
    world.store.close()
    restore(backup, destination, bot_stopped=True)
    reopened = World(destination)
    assert raw(reopened, guild=9999, rng=Draws(2,10))['total'] == 13
    assert remaining(reopened, 'luck') == [-1] and remaining(reopened, 'shift') == [-1]
    assert reopened.store.db.execute('SELECT count(*) FROM rig_audit').fetchone()[0] == 4
    exported = json.dumps(reopened.call('export')['data']).lower()
    assert all(word not in exported for word in ['rig_rules', 'rig_audit', 'rigger', 'natural'])
    reopened.store.close()


def test_commands_always_sync_globally_with_optional_fast_guild_mirror(world):
    async def run():
        bot = HeroBot(world.game, development_guild=100)
        bot.tree.sync = AsyncMock(return_value=bot.tree.get_commands())
        await bot.setup_hook()
        assert bot.tree.sync.await_count == 2
        assert bot.tree.sync.await_args_list[0].kwargs == {}
        assert bot.tree.sync.await_args_list[1].kwargs['guild'].id == 100
        assert {c.name for c in bot.tree.get_commands()} == {c.name for c in bot.tree.get_commands(guild=bot.tree.sync.await_args_list[1].kwargs['guild'])}
        assert len(SPECS) == 85
        assert 'rigger' not in ''.join(help_text(x) for x in ['quick', 'rolls', 'commands']).lower()
        await bot.close()
    asyncio.run(run())
