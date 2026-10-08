# Version 2.0.0 — October 8, 2026

- Replaced stacked creator queues with **one lasting luck setting and one next-roll override**. `!Rigger NUMBER`, `force NUMBER`, `shift +N/-N`, `luck good/bad/normal`, `status`, and `off` are the entire interface. Targets are optional, commands tolerate capitalization and surrounding spaces, and no server ID is needed.
- A new force or shift replaces the old override and applies once to a matching numeric roll. Impossible numbers produce legal bounded results instead of leaving a stuck queue. Text dice and character stat assignment are unaffected. Legacy queues are retained for recovery but never executed; new controls initially start at normal.
- Added **`/hero roll`**: saves a balanced random d10/d8/d8/d6 starting assignment before or after creation. Creation applies saved stats automatically. Repeat calls cannot farm rerolls, overwrite manual choices, or reset earned growth. Health and Energy stay fixed.
- Consolidated public menus from **20 roots / 85 commands to 8 roots / 74 commands**. GM battle, enemy, objective, session, mission, and zone tools live under `/gm`. `/help` includes cards and the handbook.
- `/hero build` combines moves, Talent, and learned item choices. `/hero help` supports both ordinary checks and battles. Capture is an attack option; Shield is a Guard option. Notes replace redundant gear/tracker setup commands.
- Turns start with the first movement or action. Invalid attempts cannot start a turn or spend its resources. Waiting rolls use **Keep / Plus Ultra** buttons; `/battle resolve` reopens them, with optional `choice:keep` / `choice:plus`.
- Added sensible optional action methods/stats, a shorter character form, a compact sheet with `details:true`, note previews, batch session attendance, and plain confirmations without internal operation names.
- Preserved heroes, Quirks, earned progression, battle data, session rewards, custom dice, FAQs, backups, and existing persistent roll-button IDs. Updated all guides and regenerated the command reference.

**245 automated tests pass**, including new regressions for the simplified flows. Keep the existing Railway volume, database path, token, IDs, and single replica. Rebuild `bot.pyz` after source or handbook changes. Earlier release notes below describe historical behavior, not the current control syntax.

# Version 1.3.0 — October 8, 2026

- Simplified the creator-only `!Rigger` DM controls to `luck good/bad/normal`, `force NUMBER`, and `shift +N/-N` or a result category. Optional player, uses, scope, and minutes arguments work in any order.
- Made creator settings universal across current and future servers, with shared use budgets and no server selection. Automatically migrates existing queues while preserving their legacy face-forcing behavior, counts, expiry, and history.
- Luck changes probabilities using complete legal numeric candidates. Exact forcing targets kept stat results or final raw totals, including visible modifiers and bonuses. Shifts apply once per command, respect bounds, and keep faces and totals consistent.
- Added lasting controls, targeted neutral luck, per-server private audit records, and bounded search for sparse custom totals. Impossible exact results remain queued; text faces still support explicit forcing.
- Registers the public slash tree globally even when an optional fast guild mirror is configured. Public command count remains **85 across 20 roots**; creator controls remain absent from player-facing Discord replies, slash menus, help, FAQs, and campaign exports.
- Fixed numeric negative-use input acceptance and overflowing clear IDs. Updated deployment instructions and corrected the old offline command count.

The automated suite passes **249 tests**, including 75 new regressions. Keep the attached Railway volume and existing variables. The private schema migration happens atomically at startup; no manual database change is required. Rebuild and upload `bot.pyz` after source changes.

# Version 1.2.0 — October 7, 2026

- Replaced the public `/dice` group with `/roll`. `/roll` defaults to 1d20 and accepts a dice expression, bonus points, keep-high/low, and optional JSON faces for `d[custom]`.
- Bonuses are shown separately and added once after selecting any kept die. Expression modifiers now work alongside keep-high/low. Invalid bonuses and text-die combinations are rejected before randomness or creator-rule consumption.
- Removed dice-create/list/remove slash commands. Per-roll faces support weighted and text dice without setup; old saved named dice remain usable.
- Rebuilt all normal replies around the supplied plain Discord message style: emoji and bold headings, inline numeric results, bold totals, and organized sheet/battle/FAQ sections. Private replies and creator DMs retain their visibility.
- Converted live battle panels to one bounded plain message. Existing panels clear their old embeds on refresh; full battle details remain in `/battle status`.
- Added Unicode-aware message splitting and repeated continuation headings. Mentions remain disabled, and user-provided names and text are escaped.
- Updated help, FAQ answers, player guides, command reference, and message examples. The public tree now has **85 slash commands across 20 root commands**.

The automated suite passes **174 tests**. Existing campaign data requires no migration. Rebuild and upload `bot.pyz` after source changes.

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
