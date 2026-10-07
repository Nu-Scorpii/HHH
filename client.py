"""Discord transport: slash commands, guided forms, persistent roll buttons."""

import asyncio
import inspect
import io
import json
import logging
import discord
from discord import app_commands
from .commands import MISSING, SPECS, help_text
from .core import Actor
from .display import embeds, result_text
from .faq import entries as faq_entries, search as faq_search
from .rules import ITEMS, MOVES, TALENTS, GameError
from .resources import handbook_bytes

log = logging.getLogger(__name__)


def actor(interaction):
    if not interaction.guild_id:
        raise GameError('Use slash commands inside your game server.')
    return Actor(interaction.guild_id, interaction.user.id, tuple(r.id for r in getattr(interaction.user, 'roles', [])))


class RollView(discord.ui.View):
    def __init__(self, bot, guild, token):
        super().__init__(timeout=None)
        self.bot, self.guild, self.token = bot, guild, token
        for ultra, label, style in [(False, 'Accept result', discord.ButtonStyle.secondary),
                                    (True, 'Plus Ultra', discord.ButtonStyle.primary)]:
            button = discord.ui.Button(label=label, style=style, custom_id=f"ua:roll:{guild}:{token}:{int(ultra)}")
            async def pressed(interaction, use_ultra=ultra):
                if interaction.guild_id != self.guild:
                    await interaction.response.send_message('Use this roll in its original server.', ephemeral=True)
                    return
                okay = await bot.execute_command(interaction, 'resolve', plus_ultra=use_ultra, pending_id=token)
                if okay and interaction.message:
                    try:
                        await interaction.message.edit(view=None)
                    except discord.HTTPException:
                        pass
            button.callback = pressed
            self.add_item(button)

    async def on_error(self, interaction, error, item):
        log.error('Roll button failed: %s', type(error).__name__)
        await self.bot.error(interaction, 'That button could not finish. Use /pending and /resolve.')


class HeroForm(discord.ui.Modal):
    def __init__(self, bot, existing=None):
        super().__init__(title='Create your student' if existing is None else 'Edit your student', timeout=900)
        self.bot, self.editing = bot, existing is not None
        existing = existing or {}
        for key, label, limit, default in [
            ('name','Real name',80,''),('hero_name','Hero name',80,''),('age','Adult age (18 or older)',3,'18'),
            ('goal','What does your hero want to achieve?',500,''),('cooperation','Why do they cooperate with classmates?',500,'')]:
            item = discord.ui.TextInput(label=label, max_length=limit, min_length=1,
                       style=discord.TextStyle.paragraph if limit > 100 else discord.TextStyle.short,
                       default=str(existing.get(key, default)))
            setattr(self, key, item)
            self.add_item(item)

    async def on_submit(self, interaction):
        try:
            age = int(str(self.age))
        except ValueError:
            await interaction.response.send_message('Use a whole-number adult age, such as 19.', ephemeral=True)
            return
        await self.bot.execute_command(interaction, 'hero_edit' if self.editing else 'hero_create', private=True,
            name=str(self.name), hero_name=str(self.hero_name), age=age, goal=str(self.goal), cooperation=str(self.cooperation))

    async def on_error(self, interaction, error):
        log.error('Hero form failed: %s', type(error).__name__)
        await self.bot.error(interaction, 'The form could not be saved. Please try again.')


class QuirkForm(discord.ui.Modal):
    def __init__(self, bot, name, reach, existing=None):
        super().__init__(title='Build your Quirk', timeout=900)
        self.bot, self.quirk_name, self.reach = bot, name, reach
        existing = existing or {}
        for key, label, hint, limit in [
            ('ability','One-sentence power','I create and shape modest amounts of ice.',500),
            ('ordinary','2–4 ordinary uses','Cover, ramps, freezing mechanisms, ranged attacks.',1000),
            ('cannot','What can it NOT do?','Control the weather or make an ice city.',1000),
            ('limits','1–2 clear limits and when they apply','Needs a surface; intense heat gives Pressure.',1000)]:
            item = discord.ui.TextInput(label=label, placeholder=hint, min_length=1, max_length=limit,
                                       style=discord.TextStyle.paragraph, default=existing.get(key, ''))
            setattr(self, key, item)
            self.add_item(item)

    async def on_submit(self, interaction):
        await self.bot.execute_command(interaction, 'hero_quirk', private=True, name=self.quirk_name, reach=self.reach,
            ability=str(self.ability), ordinary=str(self.ordinary), cannot=str(self.cannot), limits=str(self.limits))

    async def on_error(self, interaction, error):
        log.error('Quirk form failed: %s', type(error).__name__)
        await self.bot.error(interaction, 'The Quirk form could not be saved. Please try again.')


class HeroBot(discord.Client):
    def __init__(self, game, *, development_guild=None):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.dm_messages = True
        # DM content is available without the privileged Message Content intent.
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.game, self.development_guild = game, development_guild
        self.tree = app_commands.CommandTree(self)
        self.board_locks = {}
        self.register_commands()
        self.tree.on_error = self.command_error

    def register_commands(self):
        groups = {}
        for spec in SPECS:
            segments = spec.path.split()
            if len(segments) == 2 and segments[0] not in groups:
                group = app_commands.Group(name=segments[0], description=f"UA Hero College {segments[0]} commands", guild_only=True)
                groups[segments[0]] = group
                self.tree.add_command(group)
            async def callback(interaction, _spec=spec, **kwargs):
                await self.run_spec(interaction, _spec, kwargs)
            parameters = [inspect.Parameter('interaction', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=discord.Interaction)]
            for option in sorted(spec.options, key=lambda x: x.default is not MISSING):
                parameters.append(inspect.Parameter(option.name, inspect.Parameter.KEYWORD_ONLY,
                                                    annotation=option.annotation, default=option.default))
            callback.__signature__ = inspect.Signature(parameters)
            callback.__name__ = spec.path.replace(' ', '_').replace('-', '_')
            command = app_commands.Command(name=segments[-1], description=spec.description, callback=callback)
            command = app_commands.describe(**{o.name:o.description[:100] for o in spec.options})(command)
            if any(o.choices for o in spec.options):
                command = app_commands.choices(**{o.name:[app_commands.Choice(name=label,value=value) for value,label in o.choices.items()]
                                                  for o in spec.options if o.choices})(command)
            if len(segments) == 1:
                command = app_commands.guild_only()(command)
                self.tree.add_command(command)
            else:
                groups[segments[0]].add_command(command)
            for option in spec.options:
                if option.name in {'enemy', 'zone', 'objective'} and not option.choices:
                    command.autocomplete(option.name)(self.autocomplete_for(option.name))
                elif spec.path == 'faq' and option.name == 'question':
                    command.autocomplete(option.name)(self.faq_autocomplete)

    async def faq_autocomplete(self, interaction, current):
        custom = self.game.store.load(interaction.guild_id).get('faq',{}) if interaction.guild_id else {}
        matches = faq_search(current[:150],'all',custom,limit=25) if current.strip() else faq_entries(custom)[:25]
        return [app_commands.Choice(name=f'{entry.key}: {entry.question}'[:100],value=entry.key) for entry in matches]

    def autocomplete_for(self, field):
        async def autocomplete(interaction, current):
            b = self.game.store.load(interaction.guild_id).get('battle') if interaction.guild_id else None
            if not b:
                return []
            if field == 'enemy':
                values = [(key, f"{key}: {e['name']}") for key,e in b['enemies'].items()]
            else:
                values = [(key,key) for key in b['zones' if field == 'zone' else 'objectives']]
            return [app_commands.Choice(name=label[:100],value=key) for key,label in values if current.lower() in label.lower()][:25]
        return autocomplete

    async def setup_hook(self):
        for row in self.game.store.db.execute('SELECT guild,state FROM campaigns').fetchall():
            state = json.loads(row['state'])
            if state.get('pending'):
                self.add_view(RollView(self, int(row['guild']), state['pending']['id']))
        if self.development_guild:
            guild = discord.Object(id=self.development_guild)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        log.info('UA Hero College connected as bot ID %s; %s server(s).', self.user.id, len(self.guilds))

    async def on_message(self, message):
        if message.author.bot:
            return
        reply = self.game.private.handle(message.author.id, message.content, is_dm=isinstance(message.channel, discord.DMChannel),
                                         guild_ids=[g.id for g in self.guilds])
        if reply:
            # Replies remain exclusively in the creator's DM channel.
            for piece in self.dm_chunks(reply):
                await message.channel.send(piece, allowed_mentions=discord.AllowedMentions.none())

    @staticmethod
    def dm_chunks(text):
        from .display import chunks
        return chunks(text, 1800)

    async def error(self, interaction, message):
        if interaction.response.is_done():
            if interaction.extras.pop('ua_deferred_private', None) is False:
                # The first followup inherits a public defer's visibility.
                # Finish that response without exposing the private error.
                await interaction.edit_original_response(content='This command could not finish. See the private reply.',
                    allowed_mentions=discord.AllowedMentions.none())
            await interaction.followup.send(message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        else:
            await interaction.response.send_message(message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    async def command_error(self, interaction, error):
        underlying = getattr(error, 'original', error)
        if isinstance(underlying, GameError):
            await self.error(interaction, str(underlying))
        else:
            log.error('Slash command failed: %s', type(underlying).__name__,
                      exc_info=(type(underlying), underlying, underlying.__traceback__))
            await self.error(interaction, 'The command could not finish. Check /pending and /battle status before retrying; the GM can correct saved state.')

    async def run_spec(self, interaction, spec, kwargs):
        try:
            acting = actor(interaction)
            kwargs = {k:(v.id if isinstance(v,(discord.Member,discord.Role)) else v) for k,v in kwargs.items()}
            if spec.special in {'create','edit','quirk'}:
                existing = self.game.execute(acting,'hero_sheet')['hero'] if spec.special != 'create' else None
                form = QuirkForm(self,kwargs['name'],kwargs['reach'],existing['quirk']) if spec.special == 'quirk' else HeroForm(self,existing)
                await interaction.response.send_modal(form)
                return
            if spec.special == 'help':
                await self.acknowledge(interaction, private=True)
                if kwargs['topic'] == 'gm':
                    self.game.execute(acting,'roster')  # Runtime role check; no admin bypass.
                await self.send_result(interaction,{'title':'Player help','text':help_text(kwargs['topic'])},private=True)
                return
            if spec.special == 'rules':
                await self.acknowledge(interaction, private=True)
                topic = kwargs['topic']
                text = (MOVES[topic]['rule'] + f" Cost: {MOVES[topic]['cost']} Energy." if topic in MOVES else ITEMS[topic] if topic in ITEMS else
                        f"{TALENTS[topic][0]}: Edge on one {TALENTS[topic][1]} roll per scene, declared before rolling." if topic in TALENTS else help_text('quick'))
                await self.send_result(interaction,{'title':'Game rules','text':text},private=True)
                return
            if spec.special == 'guide':
                await self.acknowledge(interaction, private=True)
                await self.reply(interaction, content='Complete player handbook:',
                    file=discord.File(io.BytesIO(handbook_bytes()),filename='PLAYER_HANDBOOK.md'),ephemeral=True)
                return
            if spec.special == 'panel':
                await self.acknowledge(interaction)
                self.game.execute(acting,'roster')
                result = self.game.execute(acting,'battle_status')
                # One panel message, capped to Discord's combined embed limit.
                board = self.panel_embeds(result)
                message = await self.reply(interaction, embeds=board,allowed_mentions=discord.AllowedMentions.none())
                self.game.execute(acting,'board_set',channel_id=interaction.channel_id,message_id=message.id)
                return
            private = spec.private
            if 'share' in kwargs:
                private = not kwargs.pop('share')
            await self.execute_command(interaction,spec.operation,private=private,**kwargs)
        except GameError as exc:
            await self.error(interaction,str(exc))

    # Client.dispatch belongs to Discord's synchronous Gateway event machinery.
    # Game commands need their own entry point so login and events still work.
    async def execute_command(self, interaction, operation_name, *, private=False, **kwargs):
        try:
            acting = actor(interaction)
            # Acknowledge within Discord's deadline before SQLite can wait for
            # a file lock. The mechanical transaction remains atomic.
            await self.acknowledge(interaction, private=private)
            result = self.game.execute(acting,operation_name,request_id=interaction.id,**kwargs)
        except GameError as exc:
            await self.error(interaction,str(exc))
            return False
        await self.send_result(interaction,result,private=private)
        await self.refresh_board(interaction.guild_id)
        return True

    async def acknowledge(self, interaction, *, private=False):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=private, thinking=True)
            interaction.extras['ua_deferred_private'] = private

    async def reply(self, interaction, **kwargs):
        if 'ua_deferred_private' in interaction.extras:
            # Fill the acknowledged response directly. Its public/private
            # setting is fixed by defer, and files use the edit attachments API.
            kwargs.pop('ephemeral', None)
            if 'file' in kwargs:
                kwargs['attachments'] = [kwargs.pop('file')]
            response = await interaction.edit_original_response(**kwargs)
        elif interaction.response.is_done():
            response = await interaction.followup.send(**kwargs, wait=True)
        else:
            response = await interaction.response.send_message(**kwargs)
        interaction.extras.pop('ua_deferred_private', None)
        return response

    async def send_result(self, interaction, result, *, private=False):
        view = RollView(self,interaction.guild_id,result['pending_id']) if result.get('type') == 'pending' else None
        if result.get('type') == 'file':
            payload = io.BytesIO(json.dumps(result['data'],ensure_ascii=False,indent=2).encode())
            await self.reply(interaction,content=result.get('text','Export'),file=discord.File(payload,filename=result['filename']),ephemeral=private,
                             allowed_mentions=discord.AllowedMentions.none())
            return
        parts = embeds(result)
        options = {'embed':parts[0], 'ephemeral':private, 'allowed_mentions':discord.AllowedMentions.none()}
        if view is not None:
            options['view'] = view
        await self.reply(interaction,**options)
        for part in parts[1:]:
            await interaction.followup.send(embed=part,ephemeral=private,allowed_mentions=discord.AllowedMentions.none())

    def panel_embeds(self, result):
        # Detailed /battle status may span messages; the pinned summary stays under 6000.
        text = result_text(result)
        if len(text) > 5500:
            text = text[:5350] + '\n… Use /battle status for the complete battle.'
        from .display import chunks
        return [discord.Embed(title='Live battle · ' + result['title'][:180],description=piece,colour=0x253E55)
                for piece in chunks(text,3500)]

    async def refresh_board(self, guild):
        lock = self.board_locks.setdefault(guild,asyncio.Lock())
        async with lock:
            state = self.game.store.load(guild)
            board = (state.get('battle') or {}).get('board')
            if not board:
                return
            try:
                channel = self.get_channel(board['channel_id']) or await self.fetch_channel(board['channel_id'])
                message = await channel.fetch_message(board['message_id'])
                result = self.game.execute(Actor(guild,self.game.owner_id),'battle_status')
                await message.edit(embeds=self.panel_embeds(result),allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException as exc:
                log.warning('Live panel unavailable: %s. GM can post /battle panel again.',type(exc).__name__)

    async def close(self):
        await super().close()
        self.game.store.close()
