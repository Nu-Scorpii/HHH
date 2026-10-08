# Verification report

Checked October 8, 2026 with Python 3.12 and the pinned dependencies.

**249 automated tests passed.** The real Discord application-command tree serialized successfully: **85 slash commands across 20 root commands**. `pip check` reports no broken requirements. Offline checks made no Discord network login.

The Railway TOML parsed successfully. The real `bot.pyz` passed offline startup from an isolated directory containing only `Dockerfile`, `requirements.txt`, `railway.toml`, and `bot.pyz`. Every Docker COPY input is present in that flat directory. The bundle contains the current Python sources and full handbook, without credentials or private documentation. Its bundled backup CLI made a complete online SQLite backup. Docker CMD and the legacy TOML start the same bundle, so startup does not depend on legacy TOML support. These checks verify the packaged layout and executable app, not a real container build or live deployment.

Covered behavior:

- Character ownership, starting arrays, GM approvals, GM-role permissions, creator-only configuration, and server isolation.
- Arbitrary numbered/weighted/text dice; bounded expressions; rejection of code-like input; Edge/Pressure cancellation.
- Creator identity and one-to-one DM restriction; exact prefix; scope/target/count/expiry; legal results; incompatible dice; queue persistence; exclusion from public menus/help/exports.
- Turn and Signature budgets, Energy costs on misses, Help/Armor, Burst targets, Guard/Shield priority, group defenses, bonus movement, hazards, Capture boss limits, objective prerequisites, healing, and Danger.
- Plus Ultra choice ownership, post-effect Health cost, waiting-roll locks, stale buttons, cancellation refunds, and duplicate interaction handling.
- Session attendance, weekly Training caps and reset boundaries, Prep choices/expiry, learned unlocks, shared growth, mission locks, and spar consent/tie costs.
- Saved-state reopening, restored decision buttons, actual Discord command argument compatibility, form limits, disabled mentions, and message/panel size limits.
- Full online SQLite backup, offline restoration, preservation of the previous database, refusal of unsafe overwrites, and Railway startup refusal when persistent storage is missing/misconfigured.
- FAQ topic browsing, exact-ID and keyword search, autocomplete, private defaults/public opt-in, editing permissions, validation rollback, server isolation, legacy saves, persistence, availability during waiting rolls, and exclusion of private controls from built-in answers.
- Railway volume-derived default database path, valid overrides, all standard Railway environment markers, and rejection of root paths, traversal, and symlink escape outside the persistent volume.

New regression coverage in version 1.3.0:

- Universal creator-only controls from a DM with no server cache/selection, including future server IDs, player targeting, scopes, shared counts, TTL boundaries, lasting rules, and targeted neutral luck.
- Final-total forcing for mixed/signed/large pools, expression modifiers, bonuses, keep-high/low, and numeric custom dice. Edge/Pressure rolls preserve their count, legal faces, and kept-value selection.
- Probability adjustments retain all natural results in a seeded distribution check; complete candidates are chosen by signed final total. Exact forces bypass luck without consuming its uses; luck and hidden shifts combine with private audit records.
- Numeric shifts occur once per pool, clamp to limits, and retain legal sparse faces. Category changes skip unavailable grades; incompatible forces remain queued without consuming a use.
- Sparse custom total search matches exhaustive legal combinations on small positive/signed pools; the search-budget fallback retains valid faces and arithmetic without freezing the bot.
- Invalid control arguments fail atomically, including negative use counts, malformed/overflowing user IDs, duplicate options, and overflowing clear IDs. Repeated receipts and failures after drawing roll back usage/audit changes.
- Tracked checks, battles, sparring, and Plus Ultra continue to use the same roll handler. Creator data stays absent from public messages and campaign exports.
- Old schemas/full backups migrate idempotently without losing campaign state or legacy queue semantics; new persistent modes and audit records survive full backup/restore and restart.
- The real Discord command tree synchronizes globally and mirrors the optional configured guild, preserving 85 public commands and hidden creator controls.

New regression coverage in version 1.2.0:

- Exact reference-style roll messages with server display names, individual dice, positive/negative bonuses, and bold totals.
- Keep-high/low selects a die before adding expression modifiers and bonus points; mixed pools retain readable arithmetic.
- Inline numeric, weighted, and text faces apply only to one roll and preserve saved dice. Invalid inputs draw no randomness and consume no creator override.
- Creator overrides preserve bonus arithmetic and remain absent from public replies. Raw rolls can be used before character creation and during a waiting tracked roll without changing campaign resources or decisions.
- Slash-command serialization includes `/roll` and excludes the entire old `/dice` group; current public help and FAQs have no removed command references.
- Plain messages, long numeric/text pools, Unicode, escaped names, private continuations, empty confirmations, and large live panels fit Discord's message limits. Existing saved panels clear their old embeds while keeping their message IDs; waiting decisions appear before roster details.

New regression coverage in version 1.1.2:

- Using the real Discord dispatcher, connect, ready, message, and interaction events reach their scheduled handlers and event waiters. This test reproduced the live `HeroBot.dispatch()` startup crash before the fix and passes afterward.
- Existing command, form, roll-button ownership, and deferred-reply tests continue to pass through the renamed game command handler.
- Rebuilt `bot.pyz` contains the corrected command handler and version 1.1.2. Its offline command validation passes.

New regression coverage in version 1.1.1:

- Mixed number/text dice reject invalid operations before randomness; copied mathematical minus signs work.
- User lists reject names, enemy IDs, role mentions, zero, and overflowing IDs instead of extracting embedded digits.
- Mend, Medical Patch, Field Scanner, and spar actions expire the helper's ordinary Help; failed actions and free Smoke use retain it.
- Reopened participants retain earned session rewards, and can be unmarked without admitting a new unapproved participant.
- Blank/path-like timezone values return friendly errors with no saved-state changes.
- Tracker deletion frees a slot without changing core stats.
- Partial Capture reducing an attack to zero preserves Guard; big Capture consumes cancelled actions despite invalid planned targets.
- Enemy objective work respects prerequisites and touch/ranged/scene range, with invalid actions rolling back their budget.
- A route blocked between group defenses triggers a new bonus choice instead of movement through a closed link.
- Discord acknowledgement precedes the game transaction; deferred exports, handbook attachments, public/private FAQ replies, ownership-checked roll buttons, and saved panel message IDs work. Modal forms still use the initial response.
- Restore preserves original corrupt database and WAL/SHM bytes, successfully restores a valid backup, rejects invalid backup JSON shapes, and leaves current data untouched when the restore source is invalid.
- Zero server IDs are rejected before database creation or Discord connection.

Earlier live releases attached persistent storage at `/data` and fixed the Discord event-dispatcher conflict. This update preserves that volume. The version 1.3.0 deployment and its startup/connection verification are reported with the delivered update; multi-server gameplay tests here use local engine/Discord test doubles, not live player messages.

Known verification limits: local tests do not use a Discord token. Channel permissions and full gameplay against live Discord, as well as reconnect behavior against a real Gateway, require separate integration checks. Docker is unavailable in the workspace; the container has not been built here. The Dockerfile runs offline command validation during its build.

Tests report an upstream Python `audioop` deprecation warning and legacy TextInput-label warnings. These do not fail validation. The bot uses no voice functionality.

To reproduce from the extracted project folder:

```bash
python -m pip install -r requirements-dev.txt
python build_release.py
python bot.pyz --check
python -m ua_bot --check
python -m pytest -q
python -m pip check
```
