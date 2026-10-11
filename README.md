# Simple Discord Dice Bot · 3.0.0

The whole bot is now custom dice rolls and one creator-only DM control. Character sheets, battles, attendance, rewards, FAQs, saved-die menus, and game rules have been removed.

## Players: `/roll`

Type `/roll` for **1d20**. Every option is optional.

| Option | What to put in it |
|---|---|
| `dice` | `1d20`, `2d17+1d8-3`, or `2d[custom]` |
| `bonus` | Extra points, such as `3` or `-2` |
| `faces` | A JSON list such as `[0,1,1,5]` or `["sun","rain","rain","storm"]` |
| `keep` | All dice, Highest die, or Lowest die |

Examples:

```text
/roll
/roll dice:1d20 bonus:3
/roll dice:2d17+1d8-3
/roll dice:2d20 keep:Highest die bonus:2
/roll faces:[0,1,1,5]
/roll dice:3d[custom] faces:[0,1,1,5] bonus:2
/roll faces:["sun","rain","rain","storm"]
```

Select the option values in Discord; the examples show what goes into each field. When `dice` is omitted and `faces` is provided, the bot automatically rolls one of your custom dice. Faces belong to that command only. Repeat a face to make it more likely. To mix several custom dice, use `dice:1d[a]+1d[b]` with `faces:{"a":[0,3,8],"b":[1,2,5]}`.

Numeric results add signed modifiers and `bonus` once, after any highest/lowest selection. Highest/lowest works with one positive pool, such as `3d20+2`. A die containing any text face always has no total and cannot use arithmetic, bonuses, or highest/lowest. Text face spelling and capitalization are preserved.

Messages stay short:

```text
🎲 Hero rolled 1d20

Rolls: 8
Bonus: +3

Total: 11
```

Dice values use code formatting and the heading and total are bold. Long rolls are split into readable messages. Input mistakes receive private errors.

Limits: 100 dice per roll, 1–1 billion sides, up to 20 expression terms, 1–1,000 faces per custom die, and whole-number bonuses/modifiers within ±1 billion. Text faces may contain 1–40 characters. No programming expressions are evaluated.

## Creator

Open the bot's DMs and send `!Rigger help`. Only the user configured as `BOT_OWNER_ID` can use it. The short instructions are in `CREATOR_ONLY.md`. The command is absent from slash-command menus and server messages are ignored. New controls use one active setting; old controls are not imported. Rigger starts **off** when upgrading to this release.

## Railway

For this existing service, retain its attached volume and database path, token, and creator ID. Replace these **four files at the repository root**, then deploy the latest commit:

```text
Dockerfile
requirements.txt
railway.toml
bot.pyz
```

Upload the extracted files, rather than the download ZIP. Keep `bot.pyz` as a file. It already contains the entire minimal runtime, so a flattened GitHub upload cannot cause a missing `ua_bot` folder build error. Railway runs `python bot.pyz`; the Dockerfile validates it during the build. Repository Root Directory should be blank or `/`. Keep one replica and a continuously running service; no public domain or HTTP healthcheck is needed.

For a new service, attach a persistent volume at **`/data`**. Set these variables through your own dashboard:

| Variable | Value |
|---|---|
| `DISCORD_TOKEN` | Your existing Discord bot token |
| `BOT_OWNER_ID` | Your own Discord user ID |
| `BOT_DB_PATH` | Optional: `/data/ua.sqlite3`; omit it to use the actual attached volume automatically |

Railway supplies `RAILWAY_VOLUME_MOUNT_PATH`; do not set it manually. The database must be inside that mount. A local default is `data/ua.sqlite3`. No server ID is needed; a previous `DISCORD_GUILD_ID` is ignored. The bot replaces the global command list and clears old server-specific commands when it connects. Discord clients may need a refresh before their cached menus update.

The bot preserves old campaign tables on the volume without loading them. New settings and the last 1,000 command receipts use separate tables. Changes and one-use consumption commit together. Redeploys preserve the new setting. A repeated recent interaction returns the same roll and does not consume a new setting.

Install the Discord application with `bot` and `applications.commands` scopes. Permit View Channel and Send Messages in the roll channel and let players use application commands. Leave the Interactions Endpoint URL empty. No privileged Gateway intents or Administrator permission are needed. Creator controls and notices require that your account can DM the bot.

## Local editing and checks

Use Python 3.12, extract the full source package, and run:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ua_bot --check
python build_release.py
python bot.pyz --check
```

For local play, copy `.env.example` to `.env`, fill in your token and creator ID, and run `python bot.pyz`. Keep credentials out of source uploads. Rebuild `bot.pyz` after editing source; Railway runs the bundle, not the loose source files. The full ZIP has the proper `ua_bot/` and `tests/` folders for editing. Four-file uploads are for deployment only.

## Troubleshooting

- Bot online but `/roll` missing: check its server installation, `applications.commands` scope, and channel permissions; refresh Discord's command menu.
- Old commands still visible: refresh Discord. Runtime logs report whether old server commands could be cleared; a reconnect retries failed cleanup.
- Volume error: attach the volume to this service and place the database under its real mount, then redeploy. Retain the original database file when updating.
- Private control not responding: DM the bot from the exact account identified by `BOT_OWNER_ID`. Use `!Rigger help` and allow DMs from the bot.
- A forced custom result did not apply: `!Rigger status` gives the private explanation. The regular roll remains valid; one-use settings clear after that attempt.

Official API reference: https://discordpy.readthedocs.io/en/stable/interactions/api.html
