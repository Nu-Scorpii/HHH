"""Regression checks for /roll math, Discord output, and existing live panels."""

import asyncio
from unittest.mock import AsyncMock
import pytest
from conftest import Fixed
from test_discord import interaction
from ua_bot.client import HeroBot
from ua_bot.commands import SPECS, help_text
from ua_bot.dice import roll_expression
from ua_bot.display import battle_panel, chunks, length, messages
from ua_bot.faq import BUILTIN
from ua_bot.rules import GameError


class Sequence:
    def __init__(self, *values):
        self.values = iter(values)
    def randint(self, low, high):
        return next(self.values)


class NeverRoll:
    def randint(self, *args):
        raise AssertionError('Invalid input must not draw dice')
    def choice(self, *args):
        raise AssertionError('Invalid input must not draw faces')


@pytest.mark.parametrize('bonus,total', [(3,11), (-2,6), (0,8)])
def test_single_roll_bonus_and_reference_format(world, bonus, total):
    world.game.rng = Fixed(8)
    result = world.call('roll',2,dice='1d20',bonus=bonus)
    expected = '🎲 **Rigel (Angel) rolled 1d20**\n\nRolls: `8`\n'
    if bonus:
        expected += f'Bonus: `{bonus:+d}`\n'
    expected += f'\n**Total: {total}**'
    assert messages(result,display_name='Rigel (Angel)') == [expected]
    assert result['dice']['total'] == total


@pytest.mark.parametrize('keep,kept,total', [('high',19,24), ('low',2,7)])
def test_keep_selects_one_die_then_adds_expression_modifier_and_bonus(keep, kept, total):
    result = roll_expression('2d20+3',{},Sequence(2,19),keep,bonus=2)
    assert result['groups'][0]['rolls'] == [2,19]
    assert result['groups'][0]['kept'] == kept
    assert result['total'] == total


def test_mixed_pools_signed_modifiers_and_bonus_have_auditable_math(world):
    result = world.call('roll',2,dice='2d17+1d8-3',bonus=4)
    assert result['dice']['total'] == 16
    text = messages(result)[0]
    assert '2d17: `5` · `5`' in text and '1d8: `5`' in text
    assert 'Modifier: `-3`' in text and 'Bonus: `+4`' in text
    assert '**Total: 16**' in text


def test_plain_roll_defaults_to_d20_and_works_without_a_hero(world):
    result = world.call('roll',2)
    assert result['dice']['expression'] == '1d20'
    assert result['dice']['total'] == 5
    assert not world.state['characters']


def test_per_roll_faces_do_not_create_or_overwrite_saved_dice(world):
    world.call('dice_create',name='custom',faces='[9]')
    before = world.state
    result = world.call('roll',2,dice='2d[custom]+1',faces='[0,1,1,5]',bonus=2)
    assert result['dice']['total'] == 3
    text = world.call('roll',2,dice='d[custom]',faces='["sun","rain","rain","storm"]')
    assert text['dice']['groups'][0]['rolls'] == ['sun']
    assert text['dice']['total'] is None and '**Total:' not in messages(text)[0]
    assert world.state == before
    assert world.call('roll',2,dice='d[custom]')['dice']['total'] == 9


@pytest.mark.parametrize('options', [
    {'bonus':1000000001}, {'bonus':-1000000001}, {'bonus':1.5}, {'bonus':True},
    {'dice':'d[custom]','faces':'["sun",4]','bonus':1},
    {'dice':'d[custom]','faces':'["sun",4]','keep':'high'},
    {'dice':'d20','faces':'[1,2]'}, {'dice':'d[custom]','faces':'[true]'},
    {'dice':'d[missing]'}, {'dice':'d20+d6','keep':'low'},
])
def test_invalid_roll_input_is_atomic_and_does_not_consume_override(world, options):
    world.game.rng = NeverRoll()
    world.game.private.handle(1,'!Rigger next any max',is_dm=True,guild_ids=[100])
    before = world.state
    with pytest.raises(GameError):
        world.call('roll',2,**options)
    assert world.state == before
    assert world.store.db.execute('SELECT remaining FROM rig_rules').fetchone()[0] == 1
    assert world.store.db.execute('SELECT count(*) FROM rig_audit').fetchone()[0] == 0


def test_override_changes_faces_then_adds_bonus_without_public_disclosure(world):
    queued = world.game.private.handle(1,'!Rigger next 2 max 1 dice',is_dm=True,guild_ids=[100])
    assert queued.startswith('Queued')
    result = world.call('roll',2,dice='2d20+1',keep='high',bonus=3)
    assert result['dice']['groups'][0]['rolls'] == [20,20]
    assert result['dice']['total'] == 24
    assert world.store.db.execute('SELECT remaining FROM rig_rules').fetchone()[0] == 0
    public = messages(result)[0].lower()
    assert not any(word in public for word in ('rigger','natural','override'))


def test_raw_roll_during_pending_check_does_not_change_resources_or_decision(world):
    world.create()
    world.call('check',2,stat='power',method='Lift rubble')
    before = world.state
    world.call('roll',2,dice='d20',bonus=3)
    assert world.state == before


def test_roll_slash_callback_uses_display_name_and_plain_content(world):
    async def run():
        bot = HeroBot(world.game)
        spec = next(s for s in SPECS if s.path == 'roll')
        i = interaction()
        await bot.run_spec(i,spec,{'dice':'1d20','bonus':3,'keep':'all','faces':''})
        sent = i.edit_original_response.call_args.kwargs
        assert sent['content'].startswith('🎲 **Rigel (Angel) rolled 1d20**')
        assert '**Total: 8**' in sent['content']
        assert 'embed' not in sent and 'view' not in sent
        assert not sent['allowed_mentions'].everyone
        await bot.close()
    asyncio.run(run())


def test_long_rolls_unicode_and_escaped_names_fit_each_message():
    result = {'type':'dice','dice':roll_expression('100d1000000000',{},Fixed(999999999),bonus=-2)}
    parts = messages(result,display_name='**@everyone** 🦸')
    assert all(length(p) <= 2000 for p in parts)
    assert '\\*\\*' in parts[0] and '@everyone' not in parts[0]
    assert '**Total: 99999999898**' in parts[-1]
    assert all(p.count('`') % 2 == 0 for p in parts)
    text_roll = {'type':'dice','dice':roll_expression('100d[custom]',{'custom':['🦸'*40]},Fixed())}
    text_parts = messages(text_roll)
    assert len(text_parts) > 1 and all(length(p) <= 2000 for p in text_parts)
    assert sum(p.count('🦸') for p in text_parts) == 4000
    split = list(chunks('🦸'*2001))
    assert ''.join(split) == '🦸'*2001 and all(length(p) <= 2000 for p in split)


def test_new_public_help_has_no_removed_dice_commands():
    public = '\n'.join(help_text(t) for t in ['commands','rolls']) + '\n'.join(e.answer for e in BUILTIN)
    assert '/roll' in public and '/dice ' not in public
    assert 'bonus:3' in public and 'faces:' in public


def test_long_private_reply_keeps_every_continuation_private(world):
    async def run():
        bot = HeroBot(world.game)
        i = interaction()
        await bot.send_result(i,{'title':'Notes','text':'🦸'*3000},private=True)
        initial = i.response.send_message.call_args.kwargs
        assert initial['ephemeral'] is True and length(initial['content']) <= 2000
        assert i.followup.send.await_count > 0
        for call in i.followup.send.call_args_list:
            assert call.kwargs['ephemeral'] is True
            assert length(call.kwargs['content']) <= 2000
            assert not call.kwargs['allowed_mentions'].users
        assert messages({'text':''}) == ['✅ **UA Hero College**\n\nDone.']
        await bot.close()
    asyncio.run(run())


def test_existing_panel_migrates_to_plain_content_and_keeps_message(world):
    async def run():
        world.create()
        world.battle(users=(2,))
        world.call('board_set',channel_id=123,message_id=456)
        bot = HeroBot(world.game)
        message = type('Message',(),{'edit':AsyncMock()})()
        channel = type('Channel',(),{'fetch_message':AsyncMock(return_value=message)})()
        bot.get_channel = lambda channel_id: channel
        await bot.refresh_board(100)
        sent = message.edit.call_args.kwargs
        assert sent['embeds'] == []
        assert sent['content'].startswith('⚔️ **Live battle')
        assert length(sent['content']) <= 2000
        assert world.state['battle']['board']['message_id'] == 456
        await bot.close()
    asyncio.run(run())


def test_large_battle_panel_prioritizes_waiting_decisions(world):
    for uid in range(2,22):
        world.create(uid)
    world.battle(users=tuple(range(2,22)))
    world.call('battle_turn',2)
    world.call('battle_attack',2,targets='e1',stat='power',method='Strike')
    result = world.call('battle_status',2)
    panel = battle_panel(result)
    assert length(panel) <= 2000
    assert 'Waiting for **Hero 2**' in panel and '/resolve' in panel
    for uid, hero in result['heroes'].items():
        if uid != '2':
            hero['hero_name'] = '*'*80
    for number in range(2,26):
        result['battle']['enemies'][f'e{number}'] = dict(result['battle']['enemies']['e1'],name='*'*80)
    crowded = battle_panel(result)
    assert length(crowded) <= 2000
    assert 'Waiting for **Hero 2**' in crowded
    assert 'More on /battle status' in crowded
