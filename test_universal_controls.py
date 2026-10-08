"""Simple universal controls: one luck setting, one override, legal arithmetic."""

import itertools
import json
import random
from datetime import timedelta
import pytest
from backup import create, restore
from conftest import Fixed, World
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
    return world.game.private.handle(1, '!Rigger ' + command, is_dm=True)


def settings(world):
    return world.game.private.load()


def raw(world, expression='d20', *, guild=100, user=2, rng=None, custom=None, keep='all', bonus=0):
    with world.store.transaction():
        return world.game.private.expression(guild, user, expression, custom or {}, keep, rng or Fixed(), bonus=bonus)


def tracked(world, *, guild=100, user=2, sides=10, edge=False, pressure=False, rng=None):
    with world.store.transaction():
        return world.game.private.stat(guild, user, 'check', 'power', sides, edge, pressure, rng or Fixed())


def consistent(result, expression, custom=None):
    dice = variables(parse(expression, custom or {}))
    faces = [value for group in result['groups'] if 'die' in group for value in group['rolls']]
    assert len(faces) == len(dice)
    assert all(die.contains(value) for value, (die, _) in zip(faces, dice))
    total = result['bonus'] + sum(g.get('modifier', 0) for g in result['groups'])
    for group in result['groups']:
        if 'die' not in group: continue
        value = sum(group['rolls']) if result['keep'] == 'all' else (max if result['keep'] == 'high' else min)(group['rolls'])
        if result['keep'] != 'all': assert group['kept'] == value
        total += group['sign'] * value
    assert result['total'] == total


def test_creator_dm_and_no_guild_selection(world):
    private = world.game.private
    for user,is_dm,text in [(2,True,'!Rigger force 8'),(1,False,'!Rigger force 8'),(1,True,'!RiggerOther force 8')]:
        assert private.handle(user,text,is_dm=is_dm) is None
    assert settings(world)['next'] is None
    assert 'One use' in dm(world, '15')
    assert raw(world, guild=999999)['total'] == 15
    assert raw(world, guild=200)['total'] == 5
    assert settings(world)['next'] is None


@pytest.mark.parametrize('prefix', ['!Rigger', '!rigger', '!RIGGER', '  !RiGgEr'])
def test_prefix_case_and_extra_whitespace_are_forgiving(world, prefix):
    assert 'One use' in world.game.private.handle(1, prefix + ' force 8  ', is_dm=True)
    assert raw(world)['total'] == 8


def test_new_override_replaces_previous_instead_of_queueing(world):
    dm(world, 'force 8')
    dm(world, 'force 15')
    dm(world, 'shift -2')
    assert raw(world)['total'] == 3
    assert raw(world)['total'] == 5
    assert 'Next roll: no override' in dm(world, 'status')


@pytest.mark.parametrize('expression,bonus,keep,wanted', [
    ('2d20',0,'all',15), ('2d17+1d8-3',6,'all',15), ('d4-2d6+9',-2,'all',-3),
    ('2d20+3',4,'high',22), ('2d20-3',-4,'low',1), ('100d1000000000',0,'all',99999999999),
])
def test_force_targets_final_total_and_retains_visible_modifiers(world, expression, bonus, keep, wanted):
    dm(world, f'force {wanted}')
    result = raw(world, expression, bonus=bonus, keep=keep)
    assert result['total'] == wanted and result['bonus'] == bonus
    consistent(result, expression)
    assert settings(world)['next'] is None


@pytest.mark.parametrize('command,expression,wanted', [('force 999','d6',6),('force -20','2d6',2),('shift +99','d6',6),('shift -99','2d6',2)])
def test_impossible_requests_do_not_get_stuck(world, command, expression, wanted):
    dm(world, command)
    result = raw(world, expression)
    assert result['total'] == wanted and settings(world)['next'] is None
    consistent(result, expression)


@pytest.mark.parametrize('edge,pressure', [(False,False),(True,False),(False,True),(True,True)])
def test_stat_overrides_preserve_edge_pressure_faces_and_count(world, edge, pressure):
    dm(world, 'force 999')
    result = tracked(world, sides=6, edge=edge, pressure=pressure, rng=Fixed(2))
    assert result['kept'] == 6
    assert len(result['rolls']) == (1 if edge == pressure else 2)
    assert all(1 <= x <= 6 for x in result['rolls'])
    assert (min if pressure and not edge else max)(result['rolls']) == 6


def test_shift_applies_once_per_pool_and_stays_secret(world):
    dm(world, 'shift +3')
    result = world.call('roll', 2, dice='2d20+2', bonus=4)
    assert result['dice']['total'] == 19
    consistent(result['dice'], '2d20+2')
    output = '\n'.join(messages(result)).lower()
    assert all(word not in output for word in ['rigger','override','natural','shift','luck'])


def test_player_target_following_person_across_servers(world):
    dm(world, 'force 8 <@!2>')
    assert raw(world, guild=200, user=3)['total'] == 5
    assert settings(world)['next'] is not None
    assert raw(world, guild=98765, user=2)['total'] == 8
    assert settings(world)['next'] is None


@pytest.mark.parametrize('direction,draws,wanted', [('good',(3,17),17),('bad',(17,3),3)])
def test_luck_is_one_persistent_setting_in_every_server(world, direction, draws, wanted):
    dm(world, f'luck {direction}')
    assert raw(world, guild=200, rng=Draws(*draws))['total'] == wanted
    world.now += timedelta(days=14)
    assert raw(world, guild=99999, rng=Draws(*draws))['total'] == wanted
    dm(world, 'luck normal')
    assert raw(world, rng=Draws(5))['total'] == 5


def test_luck_changes_probabilities_without_guaranteeing_a_number(world):
    averages={}
    for direction in ['normal','good','bad']:
        dm(world, f'luck {direction}')
        rng=random.Random(42)
        with world.store.transaction():
            values=[world.game.private.stat(100,2,'check','power',10,False,False,rng)['kept'] for _ in range(600)]
        assert set(values)==set(range(1,11))
        averages[direction]=sum(values)/len(values)
    assert averages['bad']+1 < averages['normal'] < averages['good']-1


def test_luck_target_replaces_previous_target(world):
    dm(world, 'luck good')
    dm(world, 'luck bad 2')
    assert raw(world, user=3, rng=Draws(5))['total']==5
    assert raw(world, user=2, rng=Draws(15,3))['total']==3
    dm(world, 'off')
    assert raw(world, rng=Draws(5))['total']==5


def test_force_wins_over_luck_shift_runs_after_luck_and_off_resets_both(world):
    dm(world, 'luck good')
    dm(world, 'force 15')
    rng=Draws(2)
    assert raw(world,rng=rng)['total']==15 and rng.count==1
    dm(world, 'shift +3')
    assert raw(world,rng=Draws(2,10))['total']==13
    assert 'Last change: 2 → 13' in dm(world,'status')
    dm(world, 'force 8')
    dm(world, 'off')
    assert settings(world)=={'luck':0,'luck_target':'any','next':None,'last':None}


def test_text_and_mixed_faces_skip_numeric_controls_without_consumption(world):
    dm(world, 'luck good')
    dm(world, 'force 8')
    assert raw(world,'d[custom]',custom={'custom':[2,'sun']},rng=Draws('sun'))['total'] is None
    assert raw(world,'d[custom]',custom={'custom':[2,'sun']},rng=Draws(2))['total']==2
    assert settings(world)['next'] is not None
    assert raw(world,rng=Draws(5))['total']==8


@pytest.mark.parametrize('keep,wanted', [('all',8),('high',7),('low',-3)])
def test_custom_numeric_dice_retain_legal_faces(world, keep, wanted):
    custom={'custom':[-3,0,4,7,7]}
    dm(world,f'force {wanted}')
    result=raw(world,'2d[custom]',custom=custom,keep=keep)
    assert result['total']==wanted
    consistent(result,'2d[custom]',custom)


def test_sparse_custom_gap_and_search_budget_never_leave_a_stuck_override(world, monkeypatch):
    custom={'custom':[0,4,7]}
    for budget in [100000,0]:
        monkeypatch.setattr('ua_bot.rigging_math.MAX_SEARCH',budget)
        dm(world,'force 9')
        result=raw(world,'2d[custom]',custom=custom)
        consistent(result,'2d[custom]',custom)
        assert settings(world)['next'] is None
        assert result['total'] in {0,4,7,8,11,14}


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



@pytest.mark.parametrize('command', ['luck +3','luck nope','force success','force 8 uses:3','force 8 scope:attack','force 8 2 3','shift up','shift 1000000000001','clear 2','audit','next any 8','server 100','force 8 <@&2>','force 8 <@2>garbage','force 8 0','force 8 18446744073709551616','force "'])
def test_invalid_or_removed_options_fail_without_changing_active_settings(world, command):
    dm(world,'force 8')
    before=settings(world)
    assert dm(world,command).startswith('Could not')
    assert settings(world)==before


def test_failed_roll_and_duplicate_receipt_do_not_spend_the_override_twice(world, monkeypatch):
    dm(world,'force 15')
    with pytest.raises(GameError): world.call('roll',2,dice='101d6')
    assert settings(world)['next'] is not None
    first=world.game.execute(Actor(200,2),'roll',request_id=12345)
    assert world.game.execute(Actor(200,2),'roll',request_id=12345)==first
    assert world.store.db.execute('SELECT count(*) FROM rig_audit').fetchone()[0]==1
    dm(world,'shift +3')
    original=world.game.private.expression
    def failure(*args,**kwargs):
        original(*args,**kwargs)
        raise GameError('Failure after rolling')
    monkeypatch.setattr(world.game.private,'expression',failure)
    with pytest.raises(GameError): world.call('roll',2)
    assert settings(world)['next']['mode']=='shift'
    assert world.store.db.execute('SELECT count(*) FROM rig_audit').fetchone()[0]==1


def test_legacy_queues_are_archived_and_new_settings_survive_backup_restore(tmp_path):
    database,backup,restored=(tmp_path/name for name in ['game.sqlite3','backup.sqlite3','restored.sqlite3'])
    w=World(database)
    w.create()
    original=w.state
    w.store.db.execute("INSERT INTO rig_rules(guild,target,outcome,scope,remaining,expires,creator) VALUES('100','any','8','any',100,0,'1')")
    w.store.db.execute('DROP TABLE simple_controls')
    w.store.close()
    w=World(database)
    assert raw(w)['total']==5 and w.state==original
    assert w.store.db.execute('SELECT remaining FROM rig_rules').fetchone()[0]==100
    dm(w,'luck bad')
    dm(w,'force 8 2')
    create(database,backup)
    w.store.close()
    restore(backup,restored,bot_stopped=True)
    w=World(restored)
    assert w.state==original
    assert raw(w,guild=98765)['total']==8
    assert raw(w,rng=Draws(10,2))['total']==2
    exported=json.dumps(w.call('export')['data']).lower()
    assert all(word not in exported for word in ['simple_controls','rig_rules','rig_audit','rigger','natural'])
    w.store.close()
