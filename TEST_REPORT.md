# Verification — 2.0.0

Validated October 8, 2026 with Python 3.12 and the pinned requirements.

| Check | Result |
|---|---|
| Automated suite | 245 passed |
| Source offline validation | 74 slash commands across 8 root commands |
| Runtime bundle offline validation | 74 slash commands across 8 root commands |
| Dependency consistency | `pip check` passes |
| Flat four-file deployment | Bundle, handbook, and backup utility work without source folders |

## Simplified flows

Saved character assignments remain balanced, belong to one player in one server, survive restarts, and are applied by creation. Duplicate interactions and repeated calls do not draw again. Manual stats, approval, growth, pending rolls, and fixed starting resources are protected. The cache is bounded and does not use creator roll controls.

Unified build choices preserve learned-option restrictions, downtime locks, omitted fields, and spent-use marks. Invalid combined choices roll back the whole change. A first movement or action starts a turn while preserving participant checks, Down restrictions, one movement/action/signature budgets, Help expiry, and rollback. Capture and Shield use their simpler public routes. One Help command works in both contexts. Batch attendance deduplicates IDs and rolls back all marks on an invalid attendee.

Creator controls are DM-only and owner-only. Tests cover shorthand, case/space tolerance, targeting across existing and future servers, one-use replacement, lasting good/bad luck, reset/status, legal faces/totals, keep-high/low, bonuses, signed pools, sparse custom totals, large dice, impossible requests, text-die exclusions, invalid input, transaction rollback, duplicate receipts, persistence, and full backups. Legacy queues remain archived and inactive. Seeded probability tests verify the expected directional luck change.

## Existing mechanics and Discord transport

The suite also checks attack/objective outcomes, enemy movement and intentions, defenses, Armor, Guard/Shield interactions, Capture action cancellation, group attacks, deferred bonus movement, Mend, support items, Plus Ultra, Energy, Talents, Help, Prep, spar ties, weekly attendance caps, unlock approvals, shared milestones, undo, cancellation, exports, startup paths, volume validation, and backup recovery.

The real discord.py tree validates nested groups and option limits. Transport mocks cover Gateway dispatch, modal limits/defaults, private errors, GM access, global synchronization, persistent buttons, duplicate interactions, plain-message styling, Unicode message lengths, escaped names/faces, disabled mentions, and live-panel conversion. Player menus/help/FAQs/exports omit private controls.

## Limits

Local tests do not log in to Discord, play a live multiplayer battle, or directly inspect production campaign data. The Docker image is built by Railway; local verification checks the same bundled runtime offline. Live deployment verification checks Railway's active release, successful command registration, and Discord connection in filtered runtime logs. The bot's current live installation has one server; universal behavior is covered by engine tests rather than a live multi-server playtest.

Python 3.12 emits an upstream `audioop` deprecation warning. Test inspection of discord.py TextInput labels produces deprecation warnings for the pinned library. Neither warning prevents commands or deployment.
