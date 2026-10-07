"""Regression coverage for reproducible bugs found during the Railway fix."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from conftest import Fixed
from test_discord import interaction
from ua_bot.client import HeroBot
from ua_bot.commands import SPECS
from ua_bot.dice import roll_expression
from ua_bot.rules import GameError, ids


@pytest.mark.parametrize('expression,keep', [
    ('d[mixed]+1', 'all'), ('-d[mixed]', 'all'),
    ('2d[mixed]', 'high'), ('2d[mixed]', 'low'),
])
def test_mixed_text_dice_reject_invalid_operations_before_rng(expression, keep):
    class NeverRoll:
        def choice(self, faces):
            raise AssertionError('Validation must happen before randomness.')
    with pytest.raises(GameError):
        roll_expression(expression, {'mixed': [4, 'sun']}, NeverRoll(), keep)


def test_mixed_text_pool_and_copied_unicode_minus():
    result = roll_expression('d6+d[mixed]', {'mixed': ['sun', 4]}, Fixed(5))
    assert result['total'] is None
    assert result['groups'][0]['rolls'] == [5]
    assert result['groups'][1]['rolls'] == ['sun']
    assert roll_expression('2d17 − 3', {}, Fixed(7))['total'] == 11


@pytest.mark.parametrize('value', ['player2', 'e2', '<@&2>', '0', '<@0>', '-2',
    '2.3', '2,word3', '<@2', str(2**64), '9'*1000])
def test_user_lists_do_not_extract_ids_from_invalid_text(value):
    with pytest.raises(GameError):
        ids(value)


def test_user_lists_accept_only_ids_and_mentions_and_deduplicate():
    assert ids(' <@2>, <@!3> 2\n4 ') == ['2', '3', '4']
    assert ids('0002,3') == ['2', '3']


@pytest.mark.parametrize('action', ['mend', 'medical_patch', 'field_scanner', 'spar'])
def test_ordinary_help_expires_when_helper_takes_an_action(world, action):
    world.create(2, moves=('mend', 'shield'))
    world.create(3)
    world.call('ordinary_help', 2, user=3, task='check', method='Set up a route')
    world.call('resource', user=3, resource='health', value=4, reason='Earlier injury')
    if action == 'mend':
        world.call('mend', 2, user=3)
    elif action == 'spar':
        world.call('spar_start', 2, opponent=3)
        world.call('spar_join', 3)
        world.call('spar_roll', 2, stat='power', method='Practice safely')
    else:
        state = world.state
        state['characters']['2']['item'] = action
        world.store.save(100, state)
        world.call('item_use', 2, user=3, question='Is the nearby doorway clear?')
    assert world.h(3)['help'] is None


def test_failed_action_preserves_help_and_free_smoke_does_not_expire_it(world):
    world.create(2, moves=('mend', 'shield'))
    world.create(3)
    world.call('ordinary_help', 2, user=3, task='check', method='Set up a route')
    before = world.state
    with pytest.raises(GameError):
        world.call('mend', 2, user=3)  # Full Health: no costs or Help lost.
    assert world.state == before
    state = world.state
    state['characters']['2']['item'] = 'smoke_capsule'
    world.store.save(100, state)
    world.call('item_use', 2, user=3)
    assert world.h(3)['help'] is not None and world.h(3)['smoke']


def test_session_rewards_survive_reopening_an_already_marked_hero(world):
    world.create()
    world.call('session_start', name='Dorm practice', side=True, prep_theme='Rescue routes')
    world.call('session_mark', user=2)
    world.call('approve', user=2, approve=False)
    world.call('session_end', summary='Everyone practiced teamwork.')
    assert world.state['session'] is None
    assert world.h()['training'] == 1
    assert world.h()['prep']['theme'] == 'Rescue routes'
    assert not world.h()['approved']


@pytest.mark.parametrize('timezone', ['', '../Europe/London', '/Etc/UTC', 'Unknown/Zone'])
def test_invalid_timezones_are_friendly_errors_and_leave_settings_unchanged(world, timezone):
    before = world.state
    with pytest.raises(GameError, match='timezone'):
        world.call('configure', timezone=timezone)
    assert world.state == before


def test_deleting_a_tracker_frees_a_slot_and_does_not_touch_core_stats(world):
    world.create()
    original_stats = world.h()['stats']
    for n in range(20):
        world.call('hero_tracker', 2, name=f'Note {n}', value='1/4')
    with pytest.raises(GameError):
        world.call('hero_tracker', 2, name='New note', value='0/4')
    world.call('hero_tracker', 2, name='Note 0')
    world.call('hero_tracker', 2, name='New note', value='0/4')
    assert len(world.h()['trackers']) == 20
    assert 'Note 0' not in world.h()['trackers']
    assert world.h()['stats'] == original_stats


def test_capture_reducing_attack_to_zero_preserves_guard(world):
    world.create(2, moves=('capture', 'shield'))
    world.create(3)
    world.battle(enemy='minion')
    world.call('battle_turn', 3)
    world.call('battle_guard', 3)
    world.call('battle_end', 3)
    world.call('battle_turn', 2)
    world.call('battle_capture', 2, enemy='e1', stat='power', method='Hold them back')
    world.call('resolve', 2)
    world.call('battle_end', 2)
    world.call('battle_phase', phase='enemies')
    world.call('enemy_attack', enemy='e1', targets='3', description='A restrained attack')
    assert world.state['battle']['incoming'] is None
    assert world.h(3)['guard'] is not None
    assert world.h(3)['health'] == 6


@pytest.mark.parametrize('operation', ['enemy_attack', 'enemy_action'])
def test_capture_cancels_action_even_if_planned_target_is_now_invalid(world, operation):
    world.create(2, moves=('capture', 'shield'))
    world.create(3)
    world.battle()
    world.game.rng = Fixed(8)
    world.call('battle_turn', 2)
    world.call('battle_capture', 2, enemy='e1', stat='power', method='Pin them')
    world.call('resolve', 2)
    world.call('battle_end', 2)
    world.end_heroes()
    world.call('position', target='3', zone='roof', reason='Correct earlier position')
    world.call('resource', user=3, resource='health', value=0, reason='Earlier injury')
    target = {'targets':'3'} if operation == 'enemy_attack' else {'objective':'unknown'}
    result = world.call(operation, enemy='e1', description='Cancelled action', **target)
    foe = world.state['battle']['enemies']['e1']
    assert 'cancels' in result['text']
    assert foe['used'] == 1 and foe['capture'] == 0
    assert world.state['battle']['incoming'] is None


@pytest.mark.parametrize('reach,zone,allowed', [
    ('touch', 'street', True), ('touch', 'lobby', False),
    ('ranged', 'lobby', True), ('ranged', 'roof', False), ('scene', 'roof', True),
])
def test_enemy_objective_range_matches_its_card(world, reach, zone, allowed):
    world.create()
    world.battle(users=(2,))
    world.call('objective_add', key='task', name='Task', goal=2, zone=zone)
    state = world.state
    state['battle']['enemies']['e1']['reach'] = reach
    world.store.save(100, state)
    world.end_heroes(users=(2,))
    if allowed:
        world.call('enemy_action', enemy='e1', objective='task', description='Work on the task')
        assert world.state['battle']['objectives']['task']['progress'] == 1
    else:
        before = world.state
        with pytest.raises(GameError, match='reach'):
            world.call('enemy_action', enemy='e1', objective='task', description='Work on the task')
        assert world.state == before


def test_reopened_participant_can_be_removed_without_allowing_new_draft_participation(world):
    world.create()
    world.call('session_start', name='Class')
    world.call('session_mark', user=2)
    world.call('approve', user=2, approve=False)
    world.call('session_mark', user=2, participated=False)
    assert world.state['session']['participants'] == []
    with pytest.raises(GameError, match='approve'):
        world.call('session_mark', user=2)


def test_enemy_objective_prerequisites_and_reach_and_invalid_action_rollback(world):
    world.create()
    world.battle(users=(2,))
    world.call('objective_add', key='route', name='Open the route', goal=1, zone='street')
    world.call('objective_add', key='evac', name='Evacuate', goal=2, zone='roof', prerequisites='route')
    world.call('objective_add', key='scene', name='Scene objective', goal=1)
    world.end_heroes(users=(2,))
    before = world.state
    with pytest.raises(GameError, match='prerequisite'):
        world.call('enemy_action', enemy='e1', description='Attempt evacuation', objective='evac')
    assert world.state == before
    world.call('objective_tick', key='route', amount=1, reason='Route opened')
    before = world.state
    with pytest.raises(GameError, match='reach'):
        world.call('enemy_action', enemy='e1', description='Attempt evacuation', objective='evac')
    assert world.state == before
    world.call('enemy_action', enemy='e1', description='Work nearby', objective='scene')
    assert world.state['battle']['objectives']['scene']['progress'] == 1


def test_bonus_destination_is_rechecked_after_the_rest_of_a_group_attack(world):
    world.create(2)
    world.create(3)
    world.battle(trait='wide')
    world.end_heroes()
    world.call('enemy_attack', enemy='e1', targets='2,3', damage=2, description='Wide blast')
    world.game.rng = Fixed(8)
    world.call('defend', 2, stat='power', method='Block', bonus_zone='lobby')
    world.call('resolve', 2)
    world.call('zone_link', first='street', second='lobby', clear=False)
    world.game.rng = Fixed(5)
    world.call('defend', 3, stat='speed', method='Dodge', bonus_zone='stay')
    result = world.call('resolve', 3)
    assert 'no longer clear' in result['text']
    assert world.state['battle']['positions']['2'] == 'street'
    assert world.state['battle']['bonus_moves'] == {'2': True}
    world.call('bonus_move', 2, zone='stay')
    assert not world.state['battle']['bonus_moves']


def test_discord_acknowledges_before_transaction_and_exports_after_defer(world):
    async def run():
        bot = HeroBot(world.game)
        i = interaction(user=1)
        execute = world.game.execute
        def checked(*args, **kwargs):
            i.response.defer.assert_awaited_once()
            return execute(*args, **kwargs)
        world.game.execute = checked
        assert await bot.dispatch(i, 'export', private=True)
        i.response.send_message.assert_not_awaited()
        i.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        i.followup.send.assert_not_awaited()
        options = i.edit_original_response.call_args.kwargs
        assert options['attachments'][0].filename == 'ua_campaign.json'
        assert 'ephemeral' not in options
        options['attachments'][0].close()
        await bot.close()
    asyncio.run(run())


def test_deferred_public_error_keeps_the_explanation_private(world):
    async def run():
        bot = HeroBot(world.game)
        i = interaction()
        assert not await bot.dispatch(i, 'configure', gm_role_id=900)
        assert 'creator' not in i.edit_original_response.call_args.kwargs['content'].lower()
        assert 'creator' in i.followup.send.call_args.args[0]
        assert i.followup.send.call_args.kwargs['ephemeral'] is True
        assert world.state['settings']['gm_role_id'] is None
        await bot.close()
    asyncio.run(run())


def test_modals_remain_initial_responses_and_guide_is_available_after_defer(world):
    async def run():
        bot = HeroBot(world.game)
        create_spec = next(s for s in SPECS if s.path == 'hero create')
        modal = interaction()
        await bot.run_spec(modal, create_spec, {})
        modal.response.send_modal.assert_awaited_once()
        modal.response.defer.assert_not_awaited()
        guide_spec = next(s for s in SPECS if s.path == 'guide')
        guide = interaction(request=778)
        await bot.run_spec(guide, guide_spec, {})
        guide.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        file = guide.edit_original_response.call_args.kwargs['attachments'][0]
        assert file.filename == 'PLAYER_HANDBOOK.md'
        assert len(file.fp.read()) > 10000
        file.close()
        await bot.close()
    asyncio.run(run())


def test_battle_panel_saves_the_deferred_response_message(world):
    async def run():
        world.create()
        world.battle(users=(2,))
        bot = HeroBot(world.game)
        i = interaction(user=1)
        i.channel_id = 123
        i.edit_original_response = AsyncMock(return_value=SimpleNamespace(id=456))
        panel_spec = next(s for s in SPECS if s.path == 'battle panel')
        await bot.run_spec(i, panel_spec, {})
        i.response.defer.assert_awaited_once_with(ephemeral=False, thinking=True)
        assert world.state['battle']['board'] == {'channel_id':123, 'message_id':456}
        await bot.close()
    asyncio.run(run())
