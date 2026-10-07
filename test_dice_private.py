import json
from datetime import timedelta
import pytest
from conftest import Fixed, World
from ua_bot.core import Actor
from ua_bot.dice import parse_faces, roll_expression, stat_roll
from ua_bot.rules import GameError


def dm(world, text, user=1, is_dm=True, guilds=(100,)):
    return world.game.private.handle(user, text, is_dm=is_dm, guild_ids=guilds)


def test_arbitrary_numbered_pools_modifiers_and_keep():
    r = roll_expression('2d17 + 1d8 - 3', {}, Fixed(7))
    assert r['total'] == 18
    assert r['groups'][0]['rolls'] == [7, 7]
    assert roll_expression('2d1000000000', {}, Fixed(999999999))['total'] == 1999999998
    assert roll_expression('2d17', {}, Fixed(7), 'high')['total'] == 7
    assert roll_expression('2d1', {}, Fixed(7), 'low')['total'] == 1


def test_custom_weighted_and_text_dice():
    assert parse_faces('[0,1,1,5]') == [0,1,1,5]
    r = roll_expression('2d[weather]', {'weather':['sun','rain','rain','storm']}, Fixed())
    assert r['total'] is None and r['groups'][0]['rolls'] == ['sun','sun']
    assert roll_expression('2d[luck]-1', {'luck':[-3,0,0,10]}, Fixed())['total'] == -7


@pytest.mark.parametrize('expression', ['0d6','101d6','1d0','1d1000000001','d6*2','__import__("os")',
                                          'd6 d8','4','1d[missing]','d6+1000000001'])
def test_invalid_or_unbounded_expressions_rejected(expression):
    with pytest.raises(GameError):
        roll_expression(expression, {}, Fixed())


@pytest.mark.parametrize('faces', ['[]','[true]','[null]','[1.5]','{"a":2}','["'+('a'*41)+'"]'])
def test_invalid_custom_faces_rejected(faces):
    with pytest.raises(GameError):
        parse_faces(faces)


def test_text_modifiers_and_keep_rejected():
    custom = {'weather':['sun']}
    for expression, keep in [('d[weather]+1','all'), ('-d[weather]','all'), ('2d[weather]','high'), ('d6+1','low')]:
        with pytest.raises(GameError):
            roll_expression(expression, custom, Fixed(), keep)


def test_edge_pressure_cancel_regardless_sources():
    assert stat_roll(10, True, True, Fixed())['mode'] == 'normal'
    assert len(stat_roll(10, True, True, Fixed())['rolls']) == 1
    assert stat_roll(10, True, False, Fixed())['mode'] == 'edge'
    assert stat_roll(10, False, True, Fixed())['mode'] == 'pressure'


def test_private_control_requires_creator_exact_prefix_and_dm(world):
    for user, is_dm, content in [(2,True,'!Rigger next any 8'),(1,False,'!Rigger next any 8'),
                                  (1,True,'!rigger next any 8'),(1,True,'!RiggerOther next any 8')]:
        assert dm(world,content,user,is_dm) is None
    assert world.store.db.execute('SELECT count(*) FROM rig_rules').fetchone()[0] == 0
    assert 'Queued' in dm(world,'!Rigger next any 8')


def test_private_rules_scope_target_count_and_priority(world):
    dm(world,'!Rigger next any miss 2 attack 60')
    dm(world,'!Rigger next 2 8 1 power 60')
    private = world.game.private
    with world.store.transaction():
        r = private.stat(100,2,'attack','power',10,True,False,Fixed(10))
        assert r['kept'] == 8 and max(r['rolls']) == 8
        # An unrelated roll does not consume the attack-only rule.
        assert private.stat(100,3,'defense','speed',8,False,False,Fixed(5))['kept'] == 5
        for user in [3,2]:
            r = private.stat(100,user,'attack','power',10,False,True,Fixed(1))
            assert r['kept'] == 1 and min(r['rolls']) == 1
        assert private.stat(100,2,'attack','power',10,False,False,Fixed(5))['kept'] == 5
    assert world.store.db.execute('SELECT count(*) FROM rig_audit').fetchone()[0] == 3


def test_incompatible_roll_does_not_consume_rule(world):
    dm(world,'!Rigger next 2 big')
    private = world.game.private
    with world.store.transaction():
        assert private.stat(100,2,'check','heart',6,False,False,Fixed(4))['kept'] == 4
        assert world.store.db.execute('SELECT remaining FROM rig_rules').fetchone()[0] == 1
        assert private.stat(100,2,'check','wits',8,False,True,Fixed(3))['rolls'] == [8,8]


def test_private_raw_pool_faces_modifiers_and_quoted_labels(world):
    dm(world,'!Rigger next 2 7 1 dice')
    r = world.call('dice_roll',2,expression='2d17+1d8-3')['dice']
    assert r['total'] == 18 and r['groups'][0]['rolls'] == [7,7]
    world.call('dice_create',name='weather',faces='["heavy rain","sun"]')
    dm(world,'!Rigger next 2 "heavy rain" 1 dice')
    assert world.call('dice_roll',2,expression='d[weather]')['dice']['groups'][0]['rolls'] == ['heavy rain']
    assert world.store.db.execute('SELECT sum(remaining) FROM rig_rules').fetchone()[0] == 0


def test_private_ttl_and_guild_isolation(world):
    assert 'select' in dm(world,'!Rigger status',guilds=(100,200))
    assert 'Selected' in dm(world,'!Rigger server 100',guilds=(100,200))
    dm(world,'!Rigger next any max 2 dice 1')
    r = world.game.execute(Actor(200,2),'dice_roll',expression='d10')
    assert r['dice']['total'] == 5
    world.now += timedelta(seconds=61)
    assert world.call('dice_roll',2,expression='d10')['dice']['total'] == 5
    assert dm(world,'!Rigger status') == 'No queued rules.'


def test_private_invalid_commands_do_not_create_rules(world):
    for text in ['!Rigger next any max 0','!Rigger next any max 101','!Rigger next any max 1 attack 0',
                 '!Rigger next any max 1 bad','!Rigger next any max nope','!Rigger next "']:
        assert dm(world,text).startswith('Could not')
    assert world.store.db.execute('SELECT count(*) FROM rig_rules').fetchone()[0] == 0


def test_creator_controls_persist_but_never_export(world, tmp_path):
    path = tmp_path / 'game.sqlite3'
    w = World(path)
    w.create()
    dm(w,'!Rigger server 100')
    dm(w,'!Rigger next 2 max')
    w.call('check',2,stat='power',method='Lift rubble')
    exported = w.call('export')['data']
    assert 'rollback' not in exported['pending']
    text = json.dumps(exported).lower()
    assert all(x not in text for x in ['rig_rules','rig_audit','rigger','private_settings','natural'])
    w.store.close()
    reopened = World(path)
    assert 'Natural' in dm(reopened,'!Rigger audit')
    assert reopened.state['pending']['roll']['kept'] == 10
    reopened.store.close()


def test_gm_role_permissions_do_not_allow_creator_configuration(world):
    world.call('configure',gm_role_id=900)
    gm = Actor(100,3,(900,))
    world.game.execute(gm,'milestone',reason='Completed mission')
    with pytest.raises(GameError):
        world.game.execute(gm,'configure',gm_role_id=901)
    assert dm(world,'!Rigger next any 8',user=3) is None
    with pytest.raises(GameError):
        world.game.execute(Actor(100,4,(999,)),'milestone',reason='Unauthorized')


def test_failed_command_does_not_consume_creator_rule(world):
    dm(world,'!Rigger next 2 max')
    with pytest.raises(GameError):
        world.call('dice_roll',2,expression='101d6')
    assert world.store.db.execute('SELECT remaining FROM rig_rules').fetchone()[0] == 1
