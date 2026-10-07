import asyncio
import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import pytest
import discord
from ua_bot.client import HeroBot, HeroForm, QuirkForm, RollView
from ua_bot.commands import MISSING, SPECS, help_text
from ua_bot.display import embeds


def interaction(user=2, request=777, roles=()):
    response = SimpleNamespace(send_message=AsyncMock(), send_modal=AsyncMock(), is_done=Mock(return_value=False))
    async def defer(**kwargs):
        response.is_done.return_value = True
    response.defer = AsyncMock(side_effect=defer)
    return SimpleNamespace(guild_id=100, user=SimpleNamespace(id=user,roles=[SimpleNamespace(id=r) for r in roles]),
                           id=request, response=response, followup=SimpleNamespace(send=AsyncMock()), message=None,
                           extras={}, edit_original_response=AsyncMock())


def test_real_slash_tree_is_valid_and_private_command_absent(world):
    async def run():
        bot = HeroBot(world.game)
        payloads = [c.to_dict(bot.tree) for c in bot.tree.get_commands()]
        seen = []
        def check(command, parent=''):
            assert 1 <= len(command['name']) <= 32
            assert len(command.get('description','')) <= 100
            assert len(command.get('options',[])) <= 25
            assert len(command.get('choices',[])) <= 25
            if command.get('type') == 1 or not parent:
                path = (parent+' '+command['name']).strip()
                if parent or not any(o.get('type') in [1,2] for o in command.get('options',[])):
                    seen.append(path)
                for option in command.get('options',[]):
                    check(option,path)
            else:
                for option in command.get('options',[]):
                    check(option,parent)
        for payload in payloads:
            check(payload)
        assert set(seen) == {s.path for s in SPECS}
        public = json.dumps(payloads)+''.join(help_text(x) for x in ['quick','create','quirks','rolls','battle','training','spar','gm','commands'])
        assert 'rigger' not in public.lower()
        assert bot.intents.guilds and bot.intents.dm_messages
        assert not bot.intents.message_content and not bot.intents.guild_messages and not bot.intents.members
        await bot.close()
    asyncio.run(run())


def test_each_slash_operation_matches_engine_arguments(world):
    for spec in SPECS:
        if spec.special:
            continue
        function = getattr(world.game,spec.operation)
        assert function.operation
        signature = inspect.signature(function)
        arguments = {o.name:None if o.default is MISSING else o.default for o in spec.options if o.name != 'share'}
        signature.bind(None,**arguments)


def test_dispatch_saves_a_roll_and_ownership_is_enforced_by_buttons(world):
    async def run():
        world.create()
        bot = HeroBot(world.game)
        first = interaction()
        assert await bot.dispatch(first,'check',stat='power',method='Lift debris')
        first.response.defer.assert_awaited_once_with(ephemeral=False, thinking=True)
        options = first.edit_original_response.call_args.kwargs
        view = options['view']
        assert isinstance(view,RollView) and view.is_persistent()
        outsider = interaction(3,778)
        await view.children[0].callback(outsider)
        assert outsider.followup.send.call_args.kwargs['ephemeral'] is True
        assert world.state['pending'] is not None
        creator = interaction(1,779)
        await view.children[1].callback(creator)
        assert world.state['pending'] is not None and not world.h()['plus_used']
        player = interaction(2,780)
        await view.children[1].callback(player)
        assert world.state['pending'] is None and world.h()['health'] == 4
        # A duplicate interaction cannot charge Health twice.
        await view.children[1].callback(player)
        assert world.h()['health'] == 4
        await bot.close()
    asyncio.run(run())


def test_guided_forms_fit_discord_limits_and_guide_exists(world):
    from pathlib import Path
    async def run():
        bot = HeroBot(world.game)
        for form in [HeroForm(bot),QuirkForm(bot,'Ice','ranged')]:
            assert len(form.children) <= 5
            for field in form.children:
                assert len(field.label) <= 45
                assert len(field.placeholder or '') <= 100
                assert field.max_length <= 4000
            assert form.to_dict()['title']
        assert (Path(__file__).resolve().parents[1]/'docs'/'PLAYER_HANDBOOK.md').is_file()
        await bot.close()
    asyncio.run(run())


def test_plain_result_omits_none_view_and_mentions_are_disabled(world):
    async def run():
        bot = HeroBot(world.game)
        i = interaction()
        await bot.send_result(i,{'text':'A completed action'},private=True)
        kwargs = i.response.send_message.call_args.kwargs
        assert 'view' not in kwargs and kwargs['ephemeral'] is True
        assert not kwargs['allowed_mentions'].everyone
        assert not kwargs['allowed_mentions'].users
        await bot.close()
    asyncio.run(run())


def test_large_output_and_panel_fit_message_embed_limits(world):
    result = {'title':'Long sheet','text':'Long notes\n'*3000}
    pieces = embeds(result)
    assert len(pieces) > 1 and all(len(e) < 6000 and len(e.description) <= 4096 for e in pieces)
    async def run():
        bot = HeroBot(world.game)
        panel = bot.panel_embeds(result)
        assert sum(len(e) for e in panel) <= 6000 and len(panel) <= 10
        await bot.close()
    asyncio.run(run())


def test_pending_buttons_restored_after_restart_without_login(world):
    async def run():
        world.create()
        world.call('check',2,stat='power',method='Lift')
        bot = HeroBot(world.game)
        bot.tree.sync = AsyncMock(return_value=[])
        await bot.setup_hook()
        assert any(v.token == world.state['pending']['id'] for v in bot.persistent_views)
        await bot.close()
    asyncio.run(run())


def test_private_command_replies_only_in_creator_one_to_one_dm(world):
    async def run():
        bot = HeroBot(world.game)
        bot._connection._guilds[100] = SimpleNamespace(id=100)
        for user,channel_type in [(2,discord.DMChannel),(1,discord.TextChannel),(1,discord.GroupChannel),(1,discord.DMChannel)]:
            channel = Mock(spec=channel_type)
            channel.send = AsyncMock()
            message = SimpleNamespace(author=SimpleNamespace(id=user,bot=False),channel=channel,
                                      content='!Rigger next any 8',guild=None if channel_type != discord.TextChannel else SimpleNamespace(id=100))
            await bot.on_message(message)
            if user == 1 and channel_type == discord.DMChannel:
                channel.send.assert_awaited_once()
            else:
                channel.send.assert_not_awaited()
        assert world.store.db.execute('SELECT count(*) FROM rig_rules').fetchone()[0] == 1
        await bot.close()
    asyncio.run(run())
