# UA Hero College Discord Bot

A playable Discord bot for the simplified MHA university AU rules developed for your campaign. You supply the story, Quirk approvals, and fictional consequences. The bot handles the game numbers, sheets, dice, turns, and rewards.

## What is included

- **85 slash commands** with guided character and Quirk forms, rule help, searchable FAQs, and a downloadable player handbook.
- Four stat dice; Health, Energy, Training, prepared moves, Talents, items, Prep, and custom personal trackers.
- Arbitrary numbered dice, mixed dice expressions, keep-high/low, weighted custom faces, and text dice.
- Plain Discord messages with bold headings, readable dice results, and bold totals. `/roll` replaces the old `/dice` group and supports an optional `bonus`.
- Cooperative battles with zones, enemy cards, turn budgets, Armor, Help, Guard, Shield, Capture, healing, group defenses, objectives, and Danger.
- Accept/Plus Ultra buttons after stat rolls, restored if the bot restarts while a decision is waiting.
- Main and side sessions, meaningful-participation rewards, weekly Training caps, unlock requests, shared milestones, and friendly sparring.
- SQLite saves after each successful command, a live battle panel, GM corrections, campaign exports, and full database backups.
- **`/faq`** browses categories or searches common questions, with autocomplete suggestions. GMs can add persistent campaign answers with `/gm faq-add` and remove them with `/gm faq-remove`.
- A private creator control described in **CREATOR_ONLY.md**. Keep the complete source package for yourself; share the player guides with players.

This is a small-group bot: each server has one active battle **or** spar and one waiting stat roll at a time. Server data is separate. A battle supports up to 20 heroes, 25 enemies, and 25 zones. All ordinary game interaction uses slash commands and their optional form/button shortcuts.

## 1. Create the Discord bot

1. Open the [Discord Developer Portal](https://discord.com/developers/applications), create an application, and give it a name.
2. On **Bot**, generate a bot token. Keep it for Railway's `DISCORD_TOKEN` variable. Do not put it in source code or send it in Discord.
3. On **Installation**, enable **Guild Install**. Set the install link's guild scopes to `bot` and `applications.commands`.
4. Give the bot **View Channels**, **Send Messages**, **Attach Files**, and **Read Message History**. Administrator permission is unnecessary. Permit these in the game channel as well. Normal replies now use plain messages.
5. Use the install link to add it to your server. Players must be allowed to use application commands in the game channel.
6. Enable Discord **User Settings → Advanced → Developer Mode**. Right-click your own account and copy your **user ID**. Right-click your server and copy its **server ID**.

Leave the Interactions Endpoint URL empty. This bot receives interactions through Discord's Gateway. It does not need a public website, public key, or privileged Message Content/Server Members/Presence intent. The creator's private command uses direct messages, whose content is available without the privileged Message Content intent.

## 2. Fix the Railway build and deploy

Start with **START_HERE.md** if you are using GitHub's web file uploader. This release is **1.2.0**.

The error `COPY ua_bot ./ua_bot ... "/ua_bot": not found` means that Docker cannot see the old source folder in its build context. An upload that flattens or omits folders, or a Railway Root Directory pointing at the wrong folder, can cause it. This version runs a prebuilt **`bot.pyz`**, which contains all bot modules, the player handbook, and the backup utility.

### GitHub web upload: four files

1. Extract the download on your computer. The project files are directly inside the archive, without an extra `ua_hero_bot/` layer.
2. Open your bot's private GitHub repository. At its top level, use **Add file → Upload files** to upload these four extracted files together:

   - `Dockerfile`
   - `requirements.txt`
   - `railway.toml`
   - `bot.pyz`

3. Commit the upload to the branch Railway deploys. Upload the extracted files, rather than the download ZIP. Keep `bot.pyz` as a file; it already contains the app. Replace the old Dockerfile and configuration as well as the bot bundle.
4. In the existing Railway service's settings, use the repository root: leave **Root Directory blank**, or use **`/`**. For a legacy service with a custom Railway config path, use **`/railway.toml`**. Use `Dockerfile` at the root. Clear an old `RAILWAY_DOCKERFILE_PATH` override or set it to `Dockerfile`.
5. Set the dashboard Start Command to **`python bot.pyz`** and the restart policy to **On Failure**, with 10 retries. The Dockerfile also supplies that start command, and the included TOML supplies the same settings for legacy services. No separate custom build command is needed.
6. Confirm storage and variables below, then redeploy the same service. A deployment still showing `COPY ua_bot` is using the old Dockerfile: check the deployed commit, branch, and Root Directory.

The other source files and documentation are for editing, learning, and local testing; the four files above are sufficient to deploy. Keep the repository private because the runtime includes creator controls. The bot does not require GitHub to preserve any source folders for this deployment.

Railway now uses Infrastructure as Code for project configuration; `railway.toml` is retained for legacy services. This deployment works through Dockerfile detection, its built-in `CMD`, and the explicit dashboard settings above, so a new service does not need TOML support. See the [official configuration guidance](https://docs.railway.com/infrastructure-as-code).

### Persistent storage and variables

Attach a **persistent volume to the bot service**, recommended mount path **`/data`**. For an existing campaign, keep its original attached volume and database path. The volume is mounted at runtime; the Docker build checks the application without opening campaign data.

Set these service variables:

| Variable | Value |
|---|---|
| `DISCORD_TOKEN` | Token from your Discord application's Bot page |
| `BOT_OWNER_ID` | Your personal Discord user ID |
| `DISCORD_GUILD_ID` | Your server ID; recommended for this single-server campaign |
| `BOT_DB_PATH` | `/data/ua.sqlite3` for a volume mounted at `/data` |

Railway supplies `RAILWAY_VOLUME_MOUNT_PATH` for an attached volume. Do not define it manually. The bot refuses to start on Railway if storage is absent or the database resolves outside that mount, including traversal or symlinks. If `BOT_DB_PATH` is omitted, it uses `ua.sqlite3` inside the actual volume mount. A custom existing database filename is supported; retain it when updating.

Use **one replica**, one region, and a continuously running service. Disable Serverless/App Sleeping, remove any cron schedule, and leave HTTP healthcheck paths and public domains unset. This is a Discord Gateway worker. The Dockerfile uses Python 3.12, installs pinned dependencies, copies `bot.pyz`, validates the bundle offline, and starts it. Railway charges follow your account's plan; check your dashboard.

Watch runtime logs for `UA Hero College connected as bot ID ...`. Then use `/help`, `/faq`, `/guide`, and `/hero sheet`. With `DISCORD_GUILD_ID` set, commands register for that server on startup. Leaving it empty registers globally; keep this choice consistent to avoid duplicate old global/server registrations. The bot must be installed in that server.

### Railway CLI alternative

Install Node.js and the CLI, then run:

```bash
npm i -g @railway/cli
railway login
```

Open a terminal inside the extracted project folder, where `Dockerfile` and `bot.pyz` are. Run:

```bash
railway link
railway service
railway up
```

Choose the project, environment, and bot service you configured. This uploads the current directory. Keep Root Directory at the repository/project root for this flat package. Deploy the project itself, rather than a parent directory containing unrelated files.

### Updating the same service

Keep the existing token, IDs, database path, volume, and single replica. Upload the four new deployment files together and redeploy the existing service. Character sheets, battles, pending rolls, sessions, FAQs, and creator settings remain in the saved database. This release requires no schema migration. Do not replace the volume or delete the database as part of this code update.

If you edit the readable Python source or handbook, rebuild the bundle before uploading it:

```bash
python build_release.py
python bot.pyz --check
```

Python does not regenerate `bot.pyz` automatically. Upload the rebuilt bundle and any changed dependency/config files together. `python -m ua_bot` still runs the source locally; Railway runs the bundle.

## 3. Start the campaign

1. As the creator, run `/gm config`. Optionally select a trusted GM role. Default Training reset: Monday at midnight, **America/New_York**. Only the creator can change access/reset settings.
2. Players use `/help topic:create`, create their heroes, and `/hero submit`. Review the submitted Quirk and mechanical choices, then `/gm approve user:@Player`.
3. Start an official session with `/session start name:First Day` and mark meaningful participants with `/session mark user:@Player`.
4. For a main mission, use `/mission start name:Campus Rescue` after players prepare their loadouts. This locks prepared choices and assigns waiting Prep.
5. Run checks and battles. Use `/session end summary:...` to award capped Training. Finish the battle before `/mission end` or safe recovery.

Players can learn at their own pace through `/help`, `/rules`, `/faq`, and `/guide`. The bot shows the actual roll before anyone chooses Plus Ultra. `/roll` shows raw dice immediately; use `/check` and battle actions for tracked game rolls.

### Simple dice rolls

`/roll` rolls 1d20. `/roll dice:1d20 bonus:3` adds 3 points to the total. Negative bonuses subtract points. Expressions such as `2d17+1d8-3` work too, and their modifiers are shown separately from the bonus. `keep:high` or `keep:low` chooses one die from a single pool before adding any modifiers or bonus.

For weighted or text dice, use `/roll dice:1d[custom] faces:["sun","rain","rain","storm"]`. Faces apply to that roll only; repeated entries add weight. Numeric faces support bonuses and keep-high/low. Dice containing text have no numeric total and cannot use bonuses, modifiers, subtraction, or keep-high/low. Previously saved named dice remain usable through `/roll dice:1d[name]`.

Discord uses lowercase slash-command names, so type `/roll`. On startup, command synchronization replaces the old `/dice` group. Existing character sheets, battles, and saved dice require no data migration. Live panels adopt the new plain-message style on their next update. See [message examples](MESSAGE_STYLE.md).

## FAQ examples

```text
/faq
/faq question:energy
/faq question:How do I make a Quirk?
/faq category:combat
/faq question:plus-ultra share:true
```

FAQ replies are private unless `share:true` is chosen. They work before character creation and while someone is deciding a waiting roll. Built-in answers cover characters, Quirks, dice, combat, recovery, progression, sparring, and using the bot.

GMs can add a campaign answer, then update it by using the same ID:

```text
/gm faq-add key:session-times question:When do we play? answer:Saturdays at 6 PM Eastern.
/faq question:session-times
/gm faq-remove key:session-times
```

Up to 50 custom answers per server are saved across restarts and appear in search suggestions. New campaign answers default to the `campaign` category. Built-in rule IDs are protected from replacement or deletion. Existing campaign saves work without migration; custom answers are included in campaign exports and full backups.

## Files to read

| File | Purpose |
|---|---|
| `START_HERE.md` | Exact fix for the screenshot and four-file GitHub upload |
| `CHANGELOG.md` | Fixes in this release |
| `bot.pyz` | Complete deployable app; run with Python 3.12 |
| `build_release.py` | Rebuild the bundle after source edits |
| `docs/PLAYER_GUIDE.md` | Quick player onboarding and common commands |
| `docs/PLAYER_HANDBOOK.md` | Complete campaign player rules; `/guide` sends this |
| `docs/GM_GUIDE.md` | Running sessions and a complete battle walkthrough |
| `docs/COMMAND_REFERENCE.md` | Every public slash command and its arguments |
| `CREATOR_ONLY.md` | Private creator controls; keep this document private |
| `backup.py` | Host-only consistent backups and offline restore |
| `tests/` | Mechanics, permissions, dice, Discord wiring, persistence, and backup checks |

## Local running and checks

Use **Python 3.12**. From the project folder:

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Then install and validate:

```bash
python -m pip install -r requirements-dev.txt
python -m ua_bot --check
python -m pytest -q
```

For local play, copy `.env.example` to `.env`, fill in the token and IDs, and keep `BOT_DB_PATH=data/ua.sqlite3`. Start with `python -m ua_bot`. Run only one copy of the bot against your live server/database. The project ignores local credentials, saves, and virtual environments during source and container uploads.

The offline check validates the real Discord command tree without a token. The package has passed **174 automated tests** locally, including Gateway event delivery and the new roll/message behavior, and its pinned dependencies pass `pip check`. Offline checks do not log in to Discord. Live deployment verification is specific to your Railway environment. The container itself has not been built in this workspace. The real bundle also passed that check from an isolated four-file upload directory, including its embedded handbook and backup command. The Dockerfile runs the same bundle validation during a build.

Warnings about optional voice libraries are harmless for this text-command bot. Python 3.12 may also show an upstream `audioop` deprecation warning; the Dockerfile pins Python 3.12.

## Recovery and troubleshooting

- **`COPY ua_bot` fails:** upload the four current deployment files at the repository root and use the root in Railway; follow START_HERE.md.
- **Commands missing:** confirm `applications.commands` scope, the bot's server installation, the server ID, and the connected log line. Restart once after fixing the configuration.
- **A command waits:** use `/pending`. The rolling player chooses a button or `/resolve`; the GM can accept an absent player's result or `/gm cancel-roll` with a reason. Other gameplay changes wait until this decision is resolved.
- **A battle cannot advance:** use `/battle status`. End the active hero turn, finish every defense and bonus movement choice, then resolve or explicitly skip enemy actions.
- **A live panel fails:** check channel permissions and use `/battle panel` again. The underlying state stays saved; `/battle status` gives the complete board if the compact panel is truncated.
- **Wrong game change:** `/gm cancel-roll` restores a waiting roll's costs. `/gm undo` reverses the latest saved campaign change. Corrections to Health/Energy/etc. use `/gm resource` with a public reason.
- **Railway storage error:** attach the volume at `/data`, set the database path correctly, and redeploy. Do not delete the volume when updating source.
- **Backups:** turn on Railway volume backups where available and keep copies away from the live volume. `/gm export` is a readable campaign snapshot, not a full restore backup. See the GM guide for `backup.py`.

## What remains the GM's decision

The bot enforces the numerical rules and ownership, but it cannot judge a fictional Quirk, invent your story, or decide whether a described advantage is deserved. Before a roll, agree on the stat, applicable Pressure/Edge, the method, target, and miss consequence. Approve prepared moves that actually fit the Quirk. Tell players when a connection has a usable anchor, an objective prerequisite has been solved, or a villain's intention changes because its original target is no longer reachable.

The main rule tables live in `ua_bot/rules.py`; command definitions live in `ua_bot/commands.py`. Mechanics are split between campaign, battle, and spar modules. Changes to rules may also require updating resource bounds, tests, and the player handbook. Rebuild `bot.pyz` with `python build_release.py` before deploying source changes.

## Official references checked for setup

- [Discord application setup](https://docs.discord.com/developers/quick-start/getting-started)
- [Discord Gateway and intents](https://docs.discord.com/developers/events/gateway)
- [discord.py interactions](https://discordpy.readthedocs.io/en/stable/interactions/api.html)
- [Docker COPY and build contexts](https://docs.docker.com/reference/dockerfile/#copy)
- [Railway Root Directory](https://docs.railway.com/deployments/monorepo)
- [Python zip applications](https://docs.python.org/3/library/zipapp.html)
- [Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles)
- [Railway volumes](https://docs.railway.com/volumes)
- [Railway configuration](https://docs.railway.com/config-as-code/reference)
- [Railway CLI](https://docs.railway.com/cli)
- [Railway volume backups](https://docs.railway.com/volumes/backups)

Setup references checked October 7, 2026. This is an unofficial fan campaign tool, not an official MHA product.
