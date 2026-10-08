"""python -m ua_bot starts the bot; --check validates it without Discord login."""

import argparse
import asyncio
import logging
import os
from pathlib import Path
import signal
from dotenv import load_dotenv
from .client import HeroBot
from .engine import Game
from .storage import Store


def database_path(environment):
    """Use Railway's real runtime volume by default; reject ephemeral overrides."""
    configured = environment.get('BOT_DB_PATH','').strip()
    railway = any(environment.get(name) for name in ['RAILWAY_ENVIRONMENT_ID','RAILWAY_PROJECT_ID','RAILWAY_SERVICE_ID'])
    if railway:
        mount = environment.get('RAILWAY_VOLUME_MOUNT_PATH','').strip()
        if not mount or not Path(mount).is_absolute():
            raise SystemExit('Railway needs an attached persistent volume, recommended mount /data. Attach it, then redeploy.')
        volume = Path(mount).resolve()
        path = Path(configured or volume/'ua.sqlite3').resolve()
        if path == volume or not path.is_relative_to(volume):
            raise SystemExit('Railway needs its database inside the persistent volume. Use BOT_DB_PATH=/data/ua.sqlite3 with a volume mounted at /data.')
        return str(path)
    return configured or 'data/ua.sqlite3'


async def validate():
    from .resources import handbook_bytes
    assert handbook_bytes(), 'The player handbook is empty.'
    store = Store(':memory:')
    bot = HeroBot(Game(store, 1))
    commands = bot.tree.get_commands()
    # Serialize the actual Discord tree: catches unsupported options and groups.
    payloads = [c.to_dict(bot.tree) for c in commands]
    assert len(payloads) <= 100
    def check(node, depth=0):
        assert 1 <= len(node['name']) <= 32
        assert len(node.get('description', '')) <= 100
        assert len(node.get('options', [])) <= 25
        assert len(node.get('choices', [])) <= 25
        assert depth <= 3
        size = len(node['name']) + len(node.get('description', ''))
        for choice in node.get('choices', []):
            assert len(choice['name']) <= 100
            size += len(choice['name']) + (len(choice['value']) if isinstance(choice['value'], str) else 0)
        return size + sum(check(child, depth + 1) for child in node.get('options', []))
    for payload in payloads:
        assert check(payload) <= 8000, f"/{payload['name']} exceeds Discord's command size limit."
    from .commands import SPECS
    print(f"Validated {len(SPECS)} slash commands across {len(commands)} root commands. No network login performed.")
    await bot.close()


async def run():
    # Explicit cwd works for both ordinary modules and a zip-imported bot.pyz.
    load_dotenv(dotenv_path=Path.cwd()/'.env')
    token = os.getenv('DISCORD_TOKEN', '').strip()
    owner = os.getenv('BOT_OWNER_ID', '').strip()
    if not token or token == 'put_your_bot_token_here' or not owner.isdecimal() or int(owner) <= 0:
        raise SystemExit('Set DISCORD_TOKEN and BOT_OWNER_ID in your environment. BOT_OWNER_ID is your Discord user ID, not the application ID.')
    path = database_path(os.environ)
    dev_guild = os.getenv('DISCORD_GUILD_ID', '').strip()
    if dev_guild and (not dev_guild.isdecimal() or int(dev_guild) <= 0):
        raise SystemExit('DISCORD_GUILD_ID must be a server ID or empty.')
    bot = HeroBot(Game(Store(path), int(owner)), development_guild=int(dev_guild) if dev_guild else None)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.close()))
        except (NotImplementedError, RuntimeError):
            pass
    try:
        async with bot:
            await bot.start(token)
    except __import__('discord').LoginFailure:
        raise SystemExit('Discord rejected the bot token. Replace DISCORD_TOKEN with the current token from the Bot page.') from None


def main():
    parser = argparse.ArgumentParser(description='UA Hero College Discord bot')
    parser.add_argument('--check', action='store_true', help='Validate commands offline without credentials')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    asyncio.run(validate() if args.check else run())


if __name__ == '__main__':
    main()
