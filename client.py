"""Custom dice and Avatar creation, with private creator controls."""

import logging
import discord
from discord import app_commands
from . import __version__
from .dice import MAX_SIDES, prepare
from .display import avatar_messages, private_messages, roll_messages, safe
from .errors import RollError

log = logging.getLogger(__name__)
NO_MENTIONS = discord.AllowedMentions.none()


class DiceBot(discord.Client):
    def __init__(self, engine):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.dm_messages = True
        # The creator uses DMs; privileged Message Content intent is unnecessary.
        super().__init__(intents=intents, allowed_mentions=NO_MENTIONS)
        self.engine = engine
        self.tree = app_commands.CommandTree(self)
        self.cleaned_guilds = set()
        self.tree.on_error = self.command_error

        @self.tree.command(name='roll', description='Roll any dice, with optional bonus points or custom faces.')
        @app_commands.guild_only()
        @app_commands.describe(dice='Examples: 1d20, 2d17+1d8-3, or 2d[custom]. Default: 1d20 or your custom die.',
                               bonus='Extra points added to the final total; negative values subtract points.',
                               faces='Optional JSON faces: [0,1,1,5] or ["sun","rain"]. Repeats add weight.',
                               keep='Add all dice, or keep the highest/lowest die in one pool.')
        @app_commands.choices(keep=[app_commands.Choice(name='All dice', value='all'),
                                   app_commands.Choice(name='Highest die', value='high'),
                                   app_commands.Choice(name='Lowest die', value='low')])
        async def roll(interaction: discord.Interaction, dice: str | None = None,
                       bonus: app_commands.Range[int, -MAX_SIDES, MAX_SIDES] = 0,
                       faces: str | None = None, keep: str = 'all'):
            await self.run_roll(interaction, dice=dice, bonus=bonus, faces=faces, keep=keep)

        @self.tree.command(name='avatar', description='Roll Avatar character IQ, six stats, origin, and bending or combat style.')
        @app_commands.guild_only()
        async def avatar(interaction: discord.Interaction):
            await self.run_avatar(interaction)

    async def setup_hook(self):
        synced = await self.tree.sync()
        log.info('Registered %s slash commands globally (v%s); /roll and /avatar ready.', len(synced), __version__)

    async def clean_guild_commands(self, guild):
        if guild.id in self.cleaned_guilds:
            return
        try:
            # Old releases could leave guild-specific game commands overriding
            # the global tree. Remove them; this bot uses global commands.
            self.tree.clear_commands(guild=guild)
            await self.tree.sync(guild=guild)
            self.cleaned_guilds.add(guild.id)
        except discord.HTTPException as exc:
            log.warning('Old guild commands could not be cleared: %s; will retry after reconnect.', type(exc).__name__)

    async def on_ready(self):
        for guild in self.guilds:
            await self.clean_guild_commands(guild)
        log.info('Dice bot connected as bot ID %s; %s server(s); version %s.', self.user.id, len(self.guilds), __version__)

    async def on_guild_join(self, guild):
        await self.clean_guild_commands(guild)

    async def on_guild_remove(self, guild):
        self.cleaned_guilds.discard(guild.id)

    async def on_message(self, message):
        if message.author.bot:
            return
        try:
            reply = self.engine.private_message(message.author.id, message.content,
                is_dm=isinstance(message.channel, discord.DMChannel), request_id=message.id)
        except Exception as exc:
            log.error('Creator command failed: %s', type(exc).__name__)
            if message.author.id != self.engine.owner_id or not isinstance(message.channel, discord.DMChannel):
                return
            reply = 'Could not save the setting. Try !Rigger status before sending it again.'
        if reply is not None:
            try:
                for part in private_messages(reply):
                    await message.channel.send(part, allowed_mentions=NO_MENTIONS)
            except discord.HTTPException as exc:
                log.warning('Creator reply could not be delivered: %s.', type(exc).__name__)

    async def error(self, interaction, text):
        message = '⚠️ ' + safe(text)
        if not interaction.response.is_done():
            await interaction.response.send_message(message, ephemeral=True, allowed_mentions=NO_MENTIONS)
        else:
            if interaction.extras.pop('roll_deferred', False):
                # Complete a public defer without making its private error public.
                await interaction.edit_original_response(content='⚠️ **Could not finish this roll.** See the private reply.', allowed_mentions=NO_MENTIONS)
            await interaction.followup.send(message, ephemeral=True, allowed_mentions=NO_MENTIONS)

    async def command_error(self, interaction, error):
        underlying = getattr(error, 'original', error)
        if isinstance(underlying, RollError):
            await self.error(interaction, str(underlying))
        else:
            log.error('Roll command failed: %s', type(underlying).__name__)
            await self.error(interaction, 'Could not finish the roll. Please try again.')

    async def run_roll(self, interaction, *, dice=None, bonus=0, faces=None, keep='all'):
        try:
            if not interaction.guild_id:
                raise RollError('Use /roll in a server.')
            plan = prepare(dice, faces=faces, bonus=bonus, keep=keep)
        except RollError as exc:
            await self.error(interaction, str(exc))
            return
        # Acknowledge before a bounded search or the database's lock wait.
        await interaction.response.defer(thinking=True)
        interaction.extras['roll_deferred'] = True
        outcome = self.engine.roll_plan(interaction.user.id, interaction.guild_id, plan, request_id=interaction.id)
        parts = roll_messages(outcome['dice'], interaction.user.display_name)
        await self.deliver_roll(interaction, parts, outcome)

    async def run_avatar(self, interaction):
        if not interaction.guild_id:
            await self.error(interaction, 'Use /avatar in a server.')
            return
        await interaction.response.defer(thinking=True)
        interaction.extras['roll_deferred'] = True
        outcome = self.engine.avatar(interaction.user.id, interaction.guild_id, request_id=interaction.id)
        parts = avatar_messages(outcome['character'], interaction.user.display_name)
        await self.deliver_roll(interaction, parts, outcome)

    async def deliver_roll(self, interaction, parts, outcome):
        await interaction.edit_original_response(content=parts[0], allowed_mentions=NO_MENTIONS)
        interaction.extras.pop('roll_deferred', None)
        for part in parts[1:]:
            await interaction.followup.send(part, allowed_mentions=NO_MENTIONS)
        if outcome['notice'] and not outcome['replayed']:
            await self.notify_creator(outcome['notice'])

    async def notify_creator(self, notice):
        try:
            owner = self.get_user(self.engine.owner_id) or await self.fetch_user(self.engine.owner_id)
            for part in private_messages(notice):
                await owner.send(part, allowed_mentions=NO_MENTIONS)
        except discord.HTTPException as exc:
            log.warning('Creator notice could not be delivered: %s; the explanation is saved for creator status.', type(exc).__name__)

    async def close(self):
        await super().close()
        if self.engine.store is not None:
            self.engine.store.close()
            self.engine.store = None
