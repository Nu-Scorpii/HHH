# Version 1.1.2 — October 7, 2026

- Fixed startup crashes after Discord login: the game command handler no longer overrides `discord.Client.dispatch`. Gateway connect/ready events, interactions, and DM messages can reach Discord's normal event handlers.
- Updated all slash-command, form, and roll-button callers to use the separate game command handler.
- Added a regression test using the real Discord event dispatcher and event waiters. It reproduces the reported `HeroBot.dispatch()` crash before the fix and verifies connect, ready, message, and interaction delivery afterward.
- Added exact steps for attaching Railway storage at `/data` and retaining the existing campaign database when deploying the corrected bundle.

The command set remains 88 slash commands. Existing campaign data requires no migration. Rebuild and upload `bot.pyz` after source changes.

# Version 1.1.1 — October 7, 2026

## Deployment and Discord

- Replaced `COPY ua_bot` and folder-dependent deployment with a prebuilt `bot.pyz`. GitHub web uploads need only four flat files. The release ZIP now contains project files at its root.
- Bundled the player handbook and backup utility. `/guide` reads the same handbook in both source and bundled deployments. Build validation checks that it is present.
- Changed Railway and Docker startup to `python bot.pyz`; added a source-to-bundle build script and exact instructions for the reported failure.
- Corrected `.env` loading when running a zip application locally, and reject a zero `DISCORD_GUILD_ID` before opening the database or connecting.
- Acknowledge commands before database transactions can wait for a lock. Complete deferred replies using Discord's original-response API, including files and battle panels. Forms still open directly. Failed public commands keep their detailed explanation in a private reply.
- Unexpected slash-command errors now include a traceback in host logs, making runtime failures diagnosable. The creator DM handler does not log private command contents.

## Dice, sheets, and sessions

- Validate a custom die's possible faces before rolling. Mixed number/text dice consistently reject numeric modifiers, subtraction, and keep-high/low rather than randomly succeeding or failing depending on the face rolled.
- Accept copied mathematical minus signs in dice expressions. Invalid JSON numbers produce a player-readable validation error.
- User-list fields accept complete IDs or user mentions. They no longer turn names such as `player2`, enemy IDs, or role mentions into player IDs.
- Leaving `/hero tracker`'s value blank deletes that tracker, freeing a slot within the 20-tracker limit.
- Ordinary Help now expires when its helper uses Mend, Medical Patch, Field Scanner, or rolls in a spar. Failed actions keep it; free Smoke use keeps it.
- Session completion preserves earned participation rewards when an already-marked character is reopened as a draft. Such a participant can also be unmarked; new participation still requires approval.
- Invalid timezone paths and blank timezone values now return a friendly error and leave reset settings unchanged.

## Battles and recovery

- An attack already at zero damage before protection no longer spends Guard. Shield follows the same rule.
- Big Capture cancels and consumes the next enemy action even if its original target or objective is now invalid. Validity checks still roll back an uncancelled invalid action without spending its budget.
- Enemy work on objectives respects completion, prerequisites, and the card's touch/ranged/scene reach. GM progress corrections remain available with a reason.
- Recheck a preselected big-defense destination after every target has defended. A newly blocked route grants a fresh bonus movement choice rather than moving through it.
- Restore can replace a corrupt database with a verified backup. It preserves the original database and WAL/SHM bytes before SQLite can modify journals during validation. A valid old database is preserved as a normal complete snapshot.
- Reject malformed campaign JSON shapes during backup validation with a clear error. Invalid restore sources leave current data untouched.

The command set remains 88 slash commands. Existing campaign data uses the same schema and requires no migration. Source, bundle, tests, updated help, and deployment instructions are included.
