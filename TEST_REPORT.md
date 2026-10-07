# Verification report

Checked October 7, 2026 with Python 3.12 and the pinned dependencies.

**147 automated tests passed.** The real Discord application-command tree serialized successfully: **88 slash commands across 20 root commands**. `pip check` reports no broken requirements. Offline checks made no Discord network login.

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

Known verification limits: no live Discord token or Railway account was supplied, so live login, command synchronization, channel permissions, reconnect behavior against Discord, and Railway deployment have not been exercised. Docker is unavailable in the workspace; the container has not been built here. The Dockerfile runs offline command validation during its build.

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
