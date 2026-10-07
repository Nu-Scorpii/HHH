from datetime import timedelta, datetime, timezone
import json
import pytest
from conftest import Fixed, World
from ua_bot.core import Actor
from ua_bot.rules import GameError


def test_bonus_movement_must_finish_before_next_round(world):
    world.create()
    world.battle(users=(2,))
    world.end_heroes(users=(2,))
    world.call('enemy_attack',enemy='e1',targets='2',description='Punch')
    world.game.rng=Fixed(8)
    world.call('defend',2,stat='speed',method='Dodge')
    world.call('resolve',2)
    with pytest.raises(GameError):
        world.call('battle_phase',phase='next')
    world.call('bonus_move',2,zone='stay')
    world.call('battle_phase',phase='next')
    assert world.state['battle']['round']==2


def test_hazard_pauses_hero_actions_until_defenses_and_bonus_finish(world):
    world.create(2);world.create(3)
    world.battle()
    world.call('battle_turn',2)
    world.call('hazard',targets='2,3',damage=1,description='Falling debris')
    for operation,kw in [('battle_move',{'zone':'lobby'}),('battle_end',{}),('battle_recover',{})]:
        with pytest.raises(GameError):
            world.call(operation,2,**kw)
    world.game.rng=Fixed(8)
    for user in (2,3):
        world.call('defend',user,stat='speed',method='Dodge')
        world.call('resolve',user)
    with pytest.raises(GameError):
        world.call('battle_end',2)
    world.call('bonus_move',2,zone='stay');world.call('bonus_move',3,zone='stay')
    world.call('battle_move',2,zone='lobby')
    world.call('battle_end',2)


def test_spar_blocks_unrelated_healing_actions(world):
    world.create(2,moves=('mend','shield'));world.create(3)
    world.call('resource',user=3,resource='health',value=4,reason='Practice injury')
    world.call('spar_start',2,opponent=3)
    world.call('spar_join',3)
    before=world.state
    with pytest.raises(GameError):
        world.call('mend',2,user=3)
    assert world.state==before


def two(world,**kwargs):
    world.create(2,**kwargs)
    world.create(3,**kwargs)
    world.battle()


def test_starting_stats_and_character_approval(world):
    world.call('hero_create',2,name='Mira',hero_name='Frostway',age=19,goal='Rescue',cooperation='Teamwork')
    with pytest.raises(GameError):
        world.call('hero_stats',2,power=10,speed=10,wits=8,heart=6)
    with pytest.raises(GameError):
        world.call('check',2,stat='power',method='Lift the door')
    assert world.h()['health']==6 and world.h()['energy']==3


def test_creation_and_shared_growth_catch_up(world):
    world.create(2)
    world.call('milestone',reason='Class milestone')
    world.call('hero_upgrade',2,stat='power')
    assert world.h()['stats']['power']==12
    world.create(3)
    assert world.call('hero_sheet',3)['pending_increases']==1
    with pytest.raises(GameError):
        world.call('hero_upgrade',2,stat='power')


def test_only_own_hero_can_change_trackers(world):
    world.create(2); world.create(3)
    world.call('hero_tracker',2,name='Dorm project',value='2/4')
    assert world.h(2)['trackers']=={'Dorm project':'2/4'}
    assert world.h(3)['trackers']=={}


def test_help_plus_heavy_hit_bypasses_armor(world):
    world.create(2);world.create(3)
    world.battle(enemy='elite',trait='armor')
    world.call('battle_turn',3)
    world.call('battle_help',3,user=2,task='attack',method='Create an opening')
    world.call('battle_end',3)
    world.call('battle_turn',2)
    world.game.rng=Fixed(8)
    r=world.call('battle_attack',2,targets='e1',stat='power',method='Heavy ice strike',move='heavy_hit')
    assert r['roll']['mode']=='edge'
    assert world.state['battle']['enemies']['e1']['health']==6  # staged, not yet applied
    world.call('resolve',2)
    assert world.state['battle']['enemies']['e1']['health']==1
    assert world.h()['energy']==2 and world.h()['help'] is None


def test_miss_spends_energy_and_action_once(world):
    two(world)
    world.game.rng=Fixed(2)
    world.call('battle_turn',2)
    world.call('battle_attack',2,targets='e1',stat='power',method='Try a heavy strike',move='heavy_hit')
    world.call('resolve',2)
    before=world.state
    with pytest.raises(GameError):
        world.call('battle_attack',2,targets='e1',stat='power',method='Another strike')
    assert world.state==before and world.h()['energy']==2


def test_pending_roll_blocks_reroll_and_old_button(world):
    world.create()
    first=world.call('check',2,stat='power',method='Lift a door')
    with pytest.raises(GameError):
        world.call('check',2,stat='power',method='Retry the same roll')
    with pytest.raises(GameError):
        world.call('resolve',2,pending_id='wrong')
    world.call('resolve',2,pending_id=first['pending_id'])
    second=world.call('check',2,stat='power',method='Lift another door')
    with pytest.raises(GameError):
        world.call('resolve',2,pending_id=first['pending_id'])
    assert world.state['pending']['id']==second['pending_id']


def test_plus_ultra_resolves_then_can_leave_down(world):
    two(world)
    world.call('resource',user=2,resource='health',value=2,reason='Existing injury')
    world.game.rng=Fixed(1)
    world.call('battle_turn',2)
    world.call('battle_attack',2,targets='e1',stat='power',method='Final heroic strike')
    world.call('resolve',2,plus_ultra=True)
    assert world.state['battle']['enemies']['e1']['health']==1
    assert world.h()['health']==0 and world.h()['plus_used']


def test_other_player_and_gm_cannot_spend_plus_ultra(world):
    world.create(2);world.create(3)
    world.call('check',2,stat='power',method='Lift')
    for actor in (1,3):
        with pytest.raises(GameError):
            world.call('resolve',actor,plus_ultra=True)
    world.call('resolve',1)  # GM can accept, without spending the player's resources
    assert not world.h()['plus_used']


def test_guard_zero_skips_defense_and_bonus(world):
    two(world)
    world.call('battle_turn',2)
    world.call('battle_guard',2)
    world.call('battle_end',2)
    world.end_heroes()
    r=world.call('enemy_attack',enemy='e1',targets='2',description='Punch')
    assert 'no defense' in r['text'] and world.state['battle']['incoming'] is None
    assert world.h()['guard'] is None
    with pytest.raises(GameError):
        world.call('defend',2,stat='speed',method='Dodge')


def test_guard_spent_even_when_defense_succeeds(world):
    two(world)
    world.call('battle_turn',2);world.call('battle_guard',2);world.call('battle_end',2)
    world.end_heroes()
    world.call('enemy_attack',enemy='e1',targets='2',damage=3,description='Heavy punch')
    assert world.h()['guard'] is None
    world.call('defend',2,stat='speed',method='Dodge',bonus_zone='stay')
    world.call('resolve',2)
    assert world.h()['health']==6


def test_shield_protects_group_and_preserves_individual_guard(world):
    world.create(2,moves=('shield','rescue_boost'))
    world.create(3)
    world.battle(trait='wide')
    world.call('battle_turn',3);world.call('battle_guard',3);world.call('battle_end',3)
    world.call('battle_turn',2);world.call('battle_shield',2);world.call('battle_end',2)
    world.call('battle_phase',phase='enemies')
    world.call('enemy_attack',enemy='e1',targets='2,3',damage=2,description='Wide blast')
    assert world.state['battle']['incoming'] is None and not world.state['battle']['shields']
    assert world.h(3)['guard'] is not None
    assert world.h(2)['health']==world.h(3)['health']==6


def test_group_attack_waits_for_all_defenses_before_moving(world):
    two(world)
    world.call('enemy_trait',enemy='e1',trait='wide')
    world.end_heroes()
    world.call('enemy_attack',enemy='e1',targets='2,3',damage=2,description='Wide blast')
    world.game.rng=Fixed(8)
    world.call('defend',2,stat='power',method='Block',bonus_zone='lobby')
    world.call('resolve',2)
    assert world.state['battle']['positions']['2']=='street'
    world.game.rng=Fixed(5)
    world.call('defend',3,stat='speed',method='Dodge',bonus_zone='stay')
    world.call('resolve',3)
    assert world.state['battle']['positions']['2']=='lobby'
    assert world.state['battle']['incoming'] is None


def test_big_defense_choice_blocks_next_enemy_action_until_answered(world):
    world.create(2);world.create(3);world.battle(enemy='boss')
    world.end_heroes()
    world.call('enemy_attack',enemy='e1',targets='2',description='Punch')
    world.game.rng=Fixed(8)
    world.call('defend',2,stat='power',method='Block')
    world.call('resolve',2)
    with pytest.raises(GameError):
        world.call('enemy_attack',enemy='e1',targets='3',description='Another punch')
    world.call('bonus_move',2,zone='lobby')
    assert world.state['battle']['positions']['2']=='lobby'


def test_capture_cancels_one_boss_action_not_both(world):
    world.create(2,moves=('capture','rescue_boost'));world.create(3)
    world.battle(enemy='boss')
    world.game.rng=Fixed(8)
    world.call('battle_turn',2)
    world.call('battle_capture',2,enemy='e1',stat='power',method='Ice restraint')
    world.call('resolve',2);world.call('battle_end',2)
    world.end_heroes()
    r=world.call('enemy_attack',enemy='e1',targets='2',description='First punch')
    assert 'cancels' in r['text'] and world.state['battle']['incoming'] is None
    world.call('enemy_attack',enemy='e1',targets='3',description='Second punch')
    assert world.state['battle']['incoming']['targets']=={'3':3}


def test_capture_partial_blocks_move_and_reduces_next_damage(world):
    world.create(2,moves=('capture','rescue_boost'));world.create(3)
    world.battle()
    world.call('battle_turn',2)
    world.call('battle_capture',2,enemy='e1',stat='power',method='Ice restraint')
    world.call('resolve',2);world.call('battle_end',2)
    world.end_heroes()
    with pytest.raises(GameError):
        world.call('enemy_move',enemy='e1',zone='lobby')
    world.call('enemy_attack',enemy='e1',targets='3',description='Punch')
    assert world.state['battle']['incoming']['targets']=={'3':1}


def test_burst_help_applies_damage_and_armor_bypass_to_only_one(world):
    world.create(2,moves=('burst','rescue_boost'));world.create(3)
    world.battle(trait='armor')
    world.call('enemy_add',name='Second',template='rival',zone='street',trait='armor')
    world.call('battle_turn',3);world.call('battle_help',3,user=2,task='attack',method='Opening');world.call('battle_end',3)
    world.call('battle_turn',2)
    world.game.rng=Fixed(8)
    world.call('battle_attack',2,targets='e1,e2',stat='power',method='Ice burst',move='burst',assisted_target='e2')
    world.call('resolve',2)
    foes=world.state['battle']['enemies']
    assert foes['e1']['health']==3 and foes['e2']['health']==1


def test_burst_rejects_targets_in_different_zones_without_spending(world):
    world.create(2,moves=('burst','rescue_boost'));world.create(3)
    world.battle()
    world.call('enemy_add',name='Second',template='rival',zone='lobby')
    world.call('battle_turn',2)
    before=world.state
    with pytest.raises(GameError):
        world.call('battle_attack',2,targets='e1,e2',stat='power',method='Burst',move='burst')
    assert world.state==before


def test_rapid_move_keeps_ordinary_action_but_blocks_second_signature(world):
    world.create(2,moves=('rapid_move','heavy_hit'));world.create(3)
    world.battle()
    world.call('battle_turn',2)
    world.call('battle_move',2,zone='lobby',mode='rapid')
    assert world.h()['energy']==2
    with pytest.raises(GameError):
        world.call('battle_attack',2,targets='e1',stat='power',method='Heavy strike',move='heavy_hit')
    assert not world.state['battle']['budget']['action']
    world.call('battle_attack',2,targets='e1',stat='power',method='Ordinary ranged strike')
    world.call('resolve',2)


def test_normal_movement_and_rush_each_one_connection(world):
    two(world)
    world.call('battle_turn',2)
    with pytest.raises(GameError):
        world.call('battle_move',2,zone='roof')
    world.call('battle_move',2,zone='lobby')
    world.call('battle_move',2,zone='roof',mode='rush')
    assert world.state['battle']['positions']['2']=='roof'
    with pytest.raises(GameError):
        world.call('battle_recover',2)


def test_prerequisite_objective_prevents_premature_rescue_boost(world):
    two(world)
    world.call('objective_add',key='route',name='Open route',goal=3)
    world.call('objective_add',key='evac',name='Evacuation',goal=4,prerequisites='route')
    world.call('battle_turn',2)
    with pytest.raises(GameError):
        world.call('battle_task',2,stat='power',method='Evacuate',objective='evac',boost=True)
    assert world.h()['energy']==3
    world.call('objective_tick',key='route',amount=3,reason='Route opened')
    world.game.rng=Fixed(8)
    world.call('battle_task',2,stat='power',method='Evacuate',objective='evac',boost=True)
    world.call('resolve',2)
    assert world.state['battle']['objectives']['evac']['progress']==3


def test_mend_revives_once_and_medical_patch_cannot_revive(world):
    world.create(2,moves=('mend','rescue_boost'));world.create(3)
    world.battle()
    world.call('resource',user=3,resource='health',value=0,reason='Down')
    world.call('battle_turn',2);world.call('mend',2,user=3)
    assert world.h(3)['health']==1 and world.h(3)['healed']
    world.call('battle_end',2)
    world.call('resource',user=3,resource='health',value=0,reason='Down again')
    world.end_heroes()
    world.call('enemy_action',enemy='e1',description='Wait')
    world.call('battle_phase',phase='next')
    world.call('resource',user=2,resource='energy',value=3,reason='Test recovery')
    world.call('battle_turn',2)
    before=world.state
    with pytest.raises(GameError):
        world.call('mend',2,user=3)
    assert world.state==before


def test_down_cheer_once_per_fight(world):
    two(world)
    world.call('resource',user=2,resource='health',value=0,reason='Down')
    world.call('battle_turn',2);world.call('battle_help',2,user=3,task='attack',method='Cheer');world.call('battle_end',2)
    world.end_heroes()
    world.call('enemy_action',enemy='e1',description='Wait')
    world.call('battle_phase',phase='next')
    world.call('battle_turn',2)
    with pytest.raises(GameError):
        world.call('battle_help',2,user=3,task='attack',method='Cheer again')


def test_danger_advances_once_per_complete_round(world):
    two(world)
    world.call('danger_set',name='Collapse',goal=1,consequence='Exit closes')
    world.end_heroes()
    world.call('enemy_action',enemy='e1',description='Wait')
    r=world.call('battle_phase',phase='next')
    assert world.state['battle']['danger']['progress']==1 and 'Exit closes' in r['text']
    assert not world.state['battle']['danger']['active']


def test_help_expires_at_helpers_next_turn(world):
    two(world)
    world.call('battle_turn',2);world.call('battle_help',2,user=3,task='attack',method='Opening');world.call('battle_end',2)
    world.end_heroes()
    world.call('enemy_action',enemy='e1',description='Wait')
    world.call('battle_phase',phase='next')
    world.call('battle_turn',2)
    assert world.h(3)['help'] is None


def test_scene_and_session_refresh_do_not_heal(world):
    world.create()
    world.call('resource',user=2,resource='health',value=3,reason='Hurt')
    world.call('resource',user=2,resource='energy',value=1,reason='Spent')
    world.call('resource',user=2,resource='talent_used',value=1,reason='Used')
    world.call('scene_new',name='Classroom')
    world.call('session_start',name='Class')
    assert world.h()['health']==3 and world.h()['energy']==1 and not world.h()['talent_used']
    world.call('rest')
    assert world.h()['health']==6 and world.h()['energy']==3


def session(world,side=False,theme=''):
    world.call('session_start',name='Practice',side=side,prep_theme=theme)
    world.call('session_mark',user=2)
    world.call('session_end',summary='Practiced together')


def test_training_weekly_cap_and_session_end_idempotency(world):
    world.create()
    for _ in range(3):
        session(world)
    assert world.h()['training']==2
    with pytest.raises(GameError):
        world.call('session_end',summary='Double award')
    world.now+=timedelta(days=7)
    session(world)
    assert world.h()['training']==3


def test_session_crossing_reset_uses_start_week(world):
    world.create()
    world.now=datetime(2026,10,5,3,59,tzinfo=timezone.utc)  # Sunday 23:59 in NY
    world.call('session_start',name='Late practice')
    world.call('session_mark',user=2)
    world.now+=timedelta(minutes=2)
    world.call('session_end',summary='After midnight')
    assert world.h()['training_weeks']=={'2026-09-28':1}


def test_side_prep_choice_next_mission_and_expiration(world):
    world.create()
    session(world,True,'Rescue')
    session(world,True,'Stealth')
    assert world.h()['prep']['theme']=='Rescue'
    world.call('hero_prep',2,replace=True)
    assert world.h()['prep']['theme']=='Stealth'
    world.call('mission_start',name='Patrol')
    assert world.h()['prep']['mission']==world.state['mission']['id']
    world.call('mission_end')
    assert world.h()['prep'] is None


def test_unlock_spends_training_only_on_approval_and_preparation_locked(world):
    world.create()
    world.call('resource',user=2,resource='training',value=3,reason='Earned')
    world.call('hero_unlock',2,kind='move',option='shield')
    assert world.h()['training']==3
    world.call('unlock_approve',user=2,kind='move',option='shield')
    assert world.h()['training']==0 and 'shield' in world.h()['known_moves']
    world.call('hero_prepare',2,first='shield',second='heavy_hit',talent='heavy_hitter')
    world.call('mission_start',name='Mission')
    with pytest.raises(GameError):
        world.call('hero_prepare',2,first='rescue_boost',second='heavy_hit',talent='heavy_hitter')


def test_spar_requires_consent_and_tie_does_not_charge_again(world):
    world.create(2);world.create(3)
    world.call('spar_start',2,opponent=3)
    with pytest.raises(GameError):
        world.call('spar_roll',2,stat='power',method='Strike')
    world.call('spar_join',3)
    for user in (2,3):
        world.call('spar_roll',user,stat='power',method='Enhanced strike',enhanced=True)
    assert world.h(2)['energy']==world.h(3)['energy']==2
    world.call('spar_roll',2,stat='power',method='Tie reroll',enhanced=True)
    assert world.h()['energy']==2
    world.game.rng=Fixed(1)
    world.call('spar_roll',3,stat='power',method='Tie reroll',enhanced=True)
    assert world.state['spar']['scores']['2']==1


def test_interaction_retry_does_not_spend_twice(world):
    two(world)
    world.call('battle_turn',2)
    a=Actor(100,2)
    kwargs=dict(targets='e1',stat='power',method='Heavy strike',move='heavy_hit')
    first=world.game.execute(a,'battle_attack',request_id='same',**kwargs)
    again=world.game.execute(a,'battle_attack',request_id='same',**kwargs)
    assert first==again and world.h()['energy']==2


def test_cancel_invalid_roll_restores_costs(world):
    two(world)
    world.call('battle_turn',2)
    before=world.state
    world.call('battle_attack',2,targets='e1',stat='power',method='Invalid action',move='heavy_hit',talent=True)
    world.call('cancel_roll',reason='Range was misread')
    assert world.state==before


def test_persist_pending_roll_and_resume_after_restart(tmp_path):
    path=tmp_path/'game.sqlite3'
    first=World(path);first.create()
    r=first.call('check',2,stat='power',method='Lift')
    first.store.close()
    second=World(path)
    assert second.state['pending']['id']==r['pending_id']
    second.call('resolve',2)
    assert second.state['pending'] is None
    second.store.close()


def test_guild_campaigns_are_isolated(world):
    world.create()
    assert world.store.load(101)['characters']=={}
    with pytest.raises(GameError):
        world.game.execute(Actor(101,2),'hero_sheet')
