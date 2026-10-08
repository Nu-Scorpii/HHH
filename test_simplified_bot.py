"""New player shortcuts must preserve resources, approvals, and turn budgets."""

import asyncio
import pytest
from conftest import Fixed, World
from test_discord import interaction
from ua_bot.client import HeroBot, HeroForm, RollView
from ua_bot.commands import MISSING, SPECS, help_text
from ua_bot.core import Actor
from ua_bot.display import length, messages
from ua_bot.rules import GameError, STATS


def draft(world, user=2):
    return world.call('hero_create', user, name='Mira', hero_name='Frostline',
                      goal='Rescue people', cooperation='Protect classmates')


class NoDraw:
    def randint(self, *args):
        raise AssertionError('A saved roll must not roll again')
    def choice(self, *args):
        raise AssertionError('A saved roll must not roll again')


class LastChoice(Fixed):
    def choice(self, values):
        return values[-1]


def test_roll_before_creation_saves_balanced_stats_and_applies_them(world):
    world.game.rng = LastChoice()
    result = world.call('hero_roll', 2)
    assert result['stats'] == dict(zip(STATS, [6, 8, 8, 10]))
    assert world.state['characters'] == {}
    assert world.state['creation_rolls']['2'] == result['stats']
    draft(world)
    h = world.h()
    assert h['stats'] == h['creation_roll'] == result['stats']
    assert (h['health'], h['energy'], h['training']) == (6, 3, 0)
    assert '2' not in world.state['creation_rolls']


def test_draft_roll_clears_submission_once_and_never_overwrites_manual_stats(world):
    draft(world)
    world.call('hero_quirk', 2, name='Ice', ability='Make ice', ordinary='Ramps',
               reach='ranged', cannot='Change weather', limits='Heat gives Pressure')
    world.call('hero_submit', 2)
    first = world.call('hero_roll', 2)
    assert not world.h()['submitted']
    world.call('hero_stats', 2, power=6, speed=8, wits=10, heart=8)
    before = world.state
    world.game.rng = NoDraw()
    assert world.call('hero_roll', 2)['stats'] == first['stats']
    assert world.state == before
    assert world.h()['stats']['power'] == 6


def test_creation_roll_survives_restart_and_duplicate_interaction(tmp_path):
    path = tmp_path / 'campaign.sqlite3'
    one = World(path)
    first = one.game.execute(Actor(100, 2), 'hero_roll', request_id=777)
    one.game.rng = NoDraw()
    assert one.game.execute(Actor(100, 2), 'hero_roll', request_id=777) == first
    one.store.close()
    two = World(path)
    try:
        two.game.rng = NoDraw()
        assert two.call('hero_roll', 2)['stats'] == first['stats']
        draft(two)
        assert two.h()['stats'] == first['stats']
    finally:
        two.store.close()


def test_creation_roll_belongs_to_player_and_server(world):
    first = world.call('hero_roll', 2)['stats']
    world.game.rng = LastChoice()
    second = world.call('hero_roll', 3)['stats']
    third = world.game.execute(Actor(200, 2), 'hero_roll')['stats']
    assert second == third and second != first
    assert world.state['creation_rolls'] == {'2': first, '3': second}
    assert world.store.load(200)['creation_rolls'] == {'2': third}


def test_creation_assignment_does_not_use_or_consume_creator_controls(world):
    private = world.game.private
    private.handle(1, '!Rigger luck bad', is_dm=True)
    private.handle(1, '!Rigger force 1', is_dm=True)
    before = private.load()
    result = world.call('hero_roll', 2)
    assert sorted(result['stats'].values()) == [6, 8, 8, 10]
    assert private.load() == before
    assert world.call('roll', 2, dice='d20')['dice']['total'] == 1


@pytest.mark.parametrize('field,value', [('approved', True), ('training', 1), ('increases_applied', 1)])
def test_new_stat_assignment_cannot_reset_established_heroes(world, field, value):
    draft(world)
    state = world.state
    state['characters']['2'][field] = value
    world.store.save(100, state)
    before = world.state
    with pytest.raises(GameError, match='Starting rolls'):
        world.call('hero_roll', 2)
    assert world.state == before


def test_saved_assignment_remains_readable_after_approval_and_during_waiting_roll(world):
    saved = world.call('hero_roll', 2)['stats']
    world.create(2)
    world.call('check', 2, stat='power', method='Lift a door')
    before = world.state
    world.game.rng = NoDraw()
    assert world.call('hero_roll', 2)['stats'] == saved
    assert world.state == before
    with pytest.raises(GameError, match='waiting roll'):
        world.call('hero_roll', 3)
    assert world.state == before


def test_creation_cache_cap_allows_existing_draft_and_frees_slot_on_creation(world):
    state = world.state
    state['creation_rolls'] = {str(n): dict(zip(STATS, [10, 8, 8, 6])) for n in range(100, 200)}
    world.store.save(100, state)
    with pytest.raises(GameError, match='list is full'):
        world.call('hero_roll', 2)
    draft(world)
    assert world.call('hero_roll', 2)['stats'] == dict(zip(STATS, [10, 8, 8, 6]))
    draft(world, 100)
    assert len(world.state['creation_rolls']) == 99
    assert world.call('hero_roll', 3)['type'] == 'creation'


def test_build_chooses_starting_loadout_in_one_transaction(world):
    draft(world)
    world.call('hero_build', 2, first='capture', second='shield', talent='quick_feet')
    h = world.h()
    assert h['moves'] == h['known_moves'] == ['capture', 'shield']
    assert h['talent'] == 'quick_feet' and h['known_talents'] == ['quick_feet']
    before = world.state
    with pytest.raises(GameError):
        world.call('hero_build', 2, first='burst', second='mend', talent='unknown')
    assert world.state == before  # Invalid Talent also rolls back the move changes.


def test_established_build_keeps_omitted_fields_and_used_marks(world):
    world.create()
    state = world.state
    h = state['characters']['2']
    h.update(known_moves=h['known_moves'] + ['capture'], known_talents=['heavy_hitter', 'quick_feet'],
             known_items=['medical_patch'], item='medical_patch', item_used=True, talent_used=True)
    world.store.save(100, state)
    world.call('hero_build', 2, first='capture', talent='quick_feet')
    h = world.h()
    assert h['moves'] == ['capture', 'rescue_boost']
    assert h['item'] == 'medical_patch' and h['item_used'] and h['talent_used']
    world.call('hero_build', 2, item='none')
    assert world.h()['item'] is None and world.h()['item_used']
    before = world.state
    with pytest.raises(GameError, match='known'):
        world.call('hero_build', 2, first='burst')
    assert world.state == before
    world.call('mission_start', name='Internship')
    before = world.state
    with pytest.raises(GameError, match='downtime'):
        world.call('hero_build', 2)
    assert world.state == before


def test_move_automatically_starts_turn_and_preserves_one_action_budget(world):
    world.create(2)
    world.create(3)
    world.battle()
    world.call('battle_move', 2, zone='lobby')
    assert world.state['battle']['active'] == '2'
    assert world.state['battle']['budget'] == {'move': True, 'action': False, 'signature': False}
    with pytest.raises(GameError, match='Another hero'):
        world.call('battle_recover', 3)
    world.call('battle_recover', 2)
    assert world.state['battle']['budget']['action']
    with pytest.raises(GameError, match='already used your action'):
        world.call('battle_recover', 2)
    world.call('battle_end', 2)
    assert world.state['battle']['active'] is None
    world.call('protect', 3)
    assert world.state['battle']['active'] == '3'
    assert world.h(3)['guard']['source'] == '3'


def test_failed_first_action_does_not_start_turn_or_expire_existing_help(world):
    world.create(2)
    world.create(3)
    world.battle()
    state = world.state
    state['characters']['3']['help'] = {'source': '2', 'task': 'attack', 'method': 'Support'}
    world.store.save(100, state)
    before = world.state
    with pytest.raises(GameError):
        world.call('strike', 2, targets='missing', move='heavy_hit')
    assert world.state == before
    assert world.state['battle']['active'] is None
    assert world.h()['energy'] == 3
    assert world.h(3)['help'] is not None


def test_outsider_cannot_autostart_and_down_hero_can_end_turn(world):
    world.create(2)
    world.create(3)
    world.battle(users=(2,))
    before = world.state
    with pytest.raises(GameError, match='participant'):
        world.call('battle_recover', 3)
    assert world.state == before
    world.call('resource', user=2, resource='health', value=0, reason='Earlier injury')
    before = world.state
    with pytest.raises(GameError, match='Down hero'):
        world.call('battle_recover', 2)
    assert world.state == before
    world.call('battle_end', 2)
    assert world.state['battle']['acted'] == ['2']
    with pytest.raises(GameError, match='participant'):
        world.call('battle_end', 2)


def test_capture_is_an_attack_choice_and_shield_is_a_guard_choice(world):
    world.create(2, moves=('capture', 'shield'))
    world.create(3, moves=('capture', 'shield'))
    world.battle()
    with pytest.raises(GameError, match='one enemy'):
        world.call('strike', 2, targets='e1,e2', move='capture')
    world.call('strike', 2, targets='e1', move='capture')
    assert world.state['pending']['effect']['kind'] == 'capture'
    assert world.h()['energy'] == 2
    world.call('roll_decision', 2, choice='keep')
    assert world.state['battle']['enemies']['e1']['capture'] == 4
    world.call('battle_end', 2)
    before = world.state
    with pytest.raises(GameError, match='Leave the player'):
        world.call('protect', 3, kind='shield', user=2)
    assert world.state == before
    world.call('protect', 3, kind='shield')
    assert world.state['battle']['shields']['3']['zone'] == 'street'
    assert world.h(3)['energy'] == 2 and world.state['battle']['budget']['signature']


def test_one_help_command_works_outside_and_inside_battle(world):
    world.create(2)
    world.create(3)
    world.call('team_help', 2, user=3)
    assert world.h(3)['help']['task'] == 'check'
    world.battle()
    world.call('team_help', 2, user=3)
    assert world.state['battle']['active'] == '2'
    assert world.state['battle']['budget']['action']
    assert world.h(3)['help']['task'] == 'attack'
    with pytest.raises(GameError, match='already used your action'):
        world.call('team_help', 2, user=3)


def test_session_start_marks_a_deduplicated_list_and_awards_side_rewards(world):
    world.create(2)
    world.create(3)
    world.call('session_open', name='Dorm practice', side=True, prep_theme='Evacuation routes',
               participants='<@2>,3,<@!2>')
    assert world.state['session']['participants'] == ['2', '3']
    world.call('session_end', summary='Practiced together')
    for user in [2, 3]:
        assert world.h(user)['training'] == 1
        assert world.h(user)['prep']['theme'] == 'Evacuation routes'


@pytest.mark.parametrize('participants', ['2,999', '2,garbage3', '2,<@&3>'])
def test_invalid_attendee_rolls_back_whole_session_and_refresh(world, participants):
    world.create(2)
    world.call('resource', user=2, resource='plus_used', value=1, reason='Used earlier')
    before = world.state
    with pytest.raises(GameError):
        world.call('session_open', name='Class', participants=participants)
    assert world.state == before
    assert world.h()['plus_used']


def test_new_gm_shortcuts_enforce_roles_and_roll_back_combined_changes(world):
    world.create(2)
    world.battle(users=(2,))
    before = world.state
    with pytest.raises(GameError, match='Only the creator'):
        world.call('edit_enemy', 2, enemy='e1', health=99)
    with pytest.raises(GameError, match='listed trait'):
        world.call('edit_enemy', enemy='e1', health=99, trait='unknown')
    assert world.state == before
    world.call('edit_enemy', enemy='e1', health=9, trait='armor')
    assert world.state['battle']['enemies']['e1']['health'] == 9
    assert 'armor' in world.state['battle']['enemies']['e1']['traits']
    world.call('edit_enemy', enemy='e1', trait='armor', enabled=False)
    assert 'armor' not in world.state['battle']['enemies']['e1']['traits']
    world.call('danger', name='Flood', consequence='Street fills', goal=3)
    world.call('danger', active=False, consequence='Valve closed')
    assert not world.state['battle']['danger']['active']


def test_battle_resolve_default_only_reopens_buttons_and_keep_is_single_use(world):
    world.create()
    world.call('check', 2, stat='power', method='Lift rubble')
    before = world.state
    result = world.call('roll_decision', 2)
    assert result['type'] == 'pending' and result['pending_id'] == before['pending']['id']
    assert world.state == before
    with pytest.raises(GameError):
        world.call('roll_decision', 3, choice='keep')
    world.game.execute(Actor(100, 2), 'roll_decision', choice='plus', request_id=901)
    world.game.execute(Actor(100, 2), 'roll_decision', choice='plus', request_id=901)
    assert world.state['pending'] is None
    assert world.h()['plus_used'] and world.h()['health'] == 4


def test_short_sheet_previews_notes_and_full_card_keeps_everything(world):
    world.create()
    long_limit = 'Heat gives Pressure. ' * 40 + 'FINALBOUNDARY'
    state = world.state
    state['characters']['2']['quirk']['limits'] = long_limit
    world.store.save(100, state)
    for n in range(20):
        world.call('hero_tracker', 2, name=f'Note {n}', value='Progress ' * 12)
    short = messages(world.call('hero_sheet', 2))
    full = '\n'.join(messages(world.call('hero_sheet', 2, details=True)))
    assert len(short) == 1 and length(short[0]) <= 2000
    assert '17 more in the full card' in short[0] and 'Note 19' not in short[0]
    assert 'FINALBOUNDARY' not in short[0] and 'FINALBOUNDARY' in full
    assert 'Note 19' in full and 'Ordinary uses:' in full
    world.call('approve', user=2, approve=False)
    submitted = world.call('hero_submit', 2)
    assert submitted['details'] and 'FINALBOUNDARY' in '\n'.join(messages(submitted))


def test_shortcuts_replace_old_public_commands_and_need_few_inputs():
    paths = {s.path for s in SPECS}
    assert {p.split()[0] for p in paths} == {'hero', 'battle', 'roll', 'check', 'spar', 'gm', 'faq', 'help'}
    assert not paths.intersection({'rules','guide','pending','resolve','help-ally','mend','item',
        'hero moves','hero talent','hero prepare','hero gear','hero tracker','battle turn',
        'battle capture','battle shield','battle help','enemy trait','objective stop-danger'})
    assert {'hero roll','hero build','hero help','hero notes','gm session start','battle resolve'} <= paths
    for path, required in [('hero roll', []), ('hero build', []), ('battle guard', []),
                           ('battle attack', ['targets']), ('check', ['stat'])]:
        spec = next(s for s in SPECS if s.path == path)
        assert [o.name for o in spec.options if o.default is MISSING] == required
    assert '/gm battle' not in help_text('commands')
    assert '/gm battle' in help_text('commands', gm=True)


def test_guided_character_form_accepts_blank_optional_fields(world):
    async def run():
        bot = HeroBot(world.game)
        form = HeroForm(bot)
        form.name._value, form.hero_name._value = 'Mira', 'Frostline'
        form.age._value = form.goal._value = form.cooperation._value = ''
        assert not form.age.required and not form.goal.required and not form.cooperation.required
        await form.on_submit(interaction())
        assert world.h()['age'] == 18 and world.h()['goal'] == 'Become a hero.'
        assert world.h()['cooperation'] == 'Protect my classmates.'
        await bot.close()
    asyncio.run(run())


def test_help_hides_gm_tools_from_players_but_shows_them_for_configured_role(world):
    async def run():
        world.call('configure', gm_role_id=42)
        bot = HeroBot(world.game)
        spec = next(s for s in SPECS if s.path == 'help')
        for request, roles, should_show in [(801, (), False), (802, (42,), True)]:
            i = interaction(request=request, roles=roles)
            await bot.run_spec(i, spec, {'topic': 'commands'})
            content = i.edit_original_response.call_args.kwargs['content']
            content += ''.join(call.kwargs['content'] for call in i.followup.send.call_args_list)
            assert ('/gm battle' in content) == should_show
        blocked = interaction(request=803)
        await bot.run_spec(blocked, spec, {'topic': 'gm'})
        assert 'Only the creator' in blocked.followup.send.call_args.args[0]
        await bot.close()
    asyncio.run(run())


def test_simpler_notes_confirmation_and_pending_buttons_are_real_discord_payloads(world):
    async def run():
        world.create()
        bot = HeroBot(world.game)
        i = interaction(request=900)
        await bot.execute_command(i, 'hero_tracker', private=True, name='Costume', value='Blue')
        assert i.edit_original_response.call_args.kwargs['content'].startswith('✅ **Done**')
        world.call('check', 2, stat='power', method='Lift rubble')
        i = interaction(request=901)
        await bot.execute_command(i, 'roll_decision')
        view = i.edit_original_response.call_args.kwargs['view']
        assert isinstance(view, RollView)
        assert [b.label for b in view.children] == ['Keep', 'Plus Ultra · −2 HP']
        await bot.close()
    asyncio.run(run())
