# Validation · 3.1.0

231 automated tests pass on Python 3.12, including all 139 previous tests and 92 new Avatar tests. Runtime dependency compatibility and the source/bundle command checks are verified during release.

Avatar tests cover every nation boundary, all three tribes, Fire family boundaries, Earth village control, the inclusive 60 bending threshold, nation-specific elements, every Nomad element, and all combat style boundaries. They check IQ, six stat values in order, and that only applicable dice are drawn. No Air element is available.

Creator tests cover direct part controls, optional Avatar spelling, force ranges, shifts, lasting luck, full-pool stats totals, modified outcomes changing subsequent branches, scoped controls ignoring ordinary rolls, cross-server player targeting, skipped conditional parts, duplicate character deliveries, request collisions, persistence, preserved 3.0 settings, and atomic rollback after a failed write. Existing custom dice, exact forcing, weighted/text faces, bonuses, keep-high/low, and creator authorization regression tests still pass.

Discord transport tests serialize the actual two-command tree (`/roll`, `/avatar`), retain minimal intents and the Gateway dispatcher, remove obsolete server commands, acknowledge before database work, keep private state and notices out of public replies, escape mentions, obey message-size limits, and reject slash commands in DMs without consuming a setting.

Source and `bot.pyz --check` validate without credentials or Discord login. Deployment tests check the exact runtime bundle and Railway persistent-volume paths. Live Railway startup and command registration are checked separately during deployment. Automated Discord transport tests use mocked interactions; they do not send test messages to players.
