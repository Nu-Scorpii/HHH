# Fix your Railway deployment — version 1.3.0

## Missing persistent volume

If runtime logs say **"Railway needs an attached persistent volume, recommended mount /data. Attach it, then redeploy."**, the build succeeded but the bot has no persistent storage.

1. Open the Railway project containing the bot service.
2. Choose **Add → Volume**, select the bot service, and enter **`/data`** as the mount path.
3. Choose **Deploy** to apply the volume attachment and redeploy the bot.
4. If `BOT_DB_PATH` is set, it must name a database inside that mount, such as `/data/ua.sqlite3`. When omitted, the bot uses that path automatically. Keep an existing campaign's volume and database filename.

Railway supplies `RAILWAY_VOLUME_MOUNT_PATH` automatically when the volume is attached. Do not set that variable yourself. The startup check protects saves from disappearing during a restart or redeploy.

If the next error mentions **`HeroBot.dispatch()`** or **`coroutine 'HeroBot.dispatch' was never awaited`**, upload this release's rebuilt **`bot.pyz`** to the repository root and redeploy the same service. Version 1.1.2 fixes a game method that conflicted with Discord's event dispatcher. Keep the attached volume; private creator settings migrate automatically at startup.

## Earlier missing-folder build failure

Your screenshot shows:

```text
COPY ua_bot ./ua_bot
"/ua_bot": not found
```

The old Dockerfile needs a folder that was not included in Railway's build files. Uploading individual Python files can lose that folder structure. A wrong Root Directory can also hide it from the build. The bot had not reached its Discord login or database startup yet.

This release packages the bot and handbook inside **one file, `bot.pyz`**. The new Dockerfile copies that file, so the missing `ua_bot` folder is no longer needed for deployment.

## 1. Extract and upload four files

Download the corrected ZIP and extract it on your computer. Open the private GitHub repository connected to your existing Railway bot service.

At the repository's top level, choose **Add file → Upload files**. Select these four files from the extracted download:

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the Python 3.12 container |
| `requirements.txt` | Installs the pinned dependencies |
| `railway.toml` | Compatibility configuration for existing legacy services |
| `bot.pyz` | Contains the complete bot, handbook, and backup utility |

Commit them together to the branch Railway deploys. Replace the old versions when prompted. The repository file list should show all four directly at its top level.

Upload the extracted files, rather than the download ZIP. Keep `bot.pyz` intact with that filename. You do not need to recreate `ua_bot/` or `docs/` in GitHub. Keep the complete source, tests, and guides from the download for your own use.

## 2. Correct Railway's service settings

Open the **same bot service** in Railway, then its **Settings**.

| Setting | Value |
|---|---|
| Root Directory | Empty, or `/` |
| Legacy Railway config path, if manually set | `/railway.toml` |
| Builder / Dockerfile | Docker; `Dockerfile` at the repository root |
| Custom Build Command | Empty; the Dockerfile handles the build |
| Start Command | `python bot.pyz` |
| Restart Policy | On Failure; 10 retries |
| Replicas | `1` |

If you previously set `RAILWAY_DOCKERFILE_PATH`, remove the override or set it to `Dockerfile`. Remove an old start override such as `python -m ua_bot`. Keep the service running continuously, with no cron schedule, Serverless/App Sleeping, or HTTP healthcheck.

Railway's official [Dockerfile documentation](https://docs.railway.com/builds/dockerfiles) explains root detection. Its [Root Directory documentation](https://docs.railway.com/deployments/monorepo) explains which files are included in a deployment.

Railway’s current [configuration guidance](https://docs.railway.com/infrastructure-as-code) uses Infrastructure as Code for new services; the TOML file is included for existing legacy services. Explicitly set the start/restart settings above. The Dockerfile itself also starts `python bot.pyz`, so this bot can run without TOML support.

## 3. Keep the saved campaign

For an existing game, keep the original attached volume and database path. Redeploying code does not require replacing either.

For a new game, attach a persistent volume to the bot service at **`/data`** and set:

```text
DISCORD_TOKEN=your existing bot token
BOT_OWNER_ID=your personal Discord user ID
# Optional fast mirror; commands also register globally:
DISCORD_GUILD_ID=your Discord server ID
BOT_DB_PATH=/data/ua.sqlite3
```

Put these values in Railway's service variables. Keep token values out of GitHub. Railway supplies `RAILWAY_VOLUME_MOUNT_PATH` automatically when a volume is attached. See [Railway volumes](https://docs.railway.com/volumes).

An existing database using a different filename or volume mount should retain its current path inside that volume. The campaign schema is unchanged. Startup automatically migrates private creator settings and preserves their counts, expiry, and history; no manual migration is needed.

## 4. Redeploy and check

Deploy the new commit on the same service. The build will copy `bot.pyz` and print:

```text
Validated 85 slash commands across 20 root commands. No network login performed.
```

After the build, runtime logs should show:

```text
UA Hero College connected as bot ID ...
```

In Discord, try `/help`, `/faq question:energy`, `/guide`, and `/hero sheet`. Confirm your existing sheet and any waiting battle are present before starting the next session.

If the build still says **`COPY ua_bot`**, it is using the old Dockerfile. Check that the four files were committed to the connected branch, at the root, and that you deployed that new commit. If it says **`bot.pyz: not found`**, upload the supplied `bot.pyz` next to the new Dockerfile.

If it builds but reports missing storage or credentials, check the attached volume and service variables; those are runtime issues after the folder-copy error has been fixed.

## If you edit the source later

With Python 3.12 and the requirements installed, run these from the full extracted project folder:

```bash
python build_release.py
python bot.pyz --check
python -m pytest -q
```

Then upload the rebuilt `bot.pyz` and any changed dependency/config files. Readable files under `ua_bot/` are the canonical source; Railway runs the bundle you upload, so source edits need this rebuild.

Read **CHANGELOG.md** for the other fixes and **TEST_REPORT.md** for verification and its limits.
