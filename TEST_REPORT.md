# Validation · 3.0.0

139 automated tests pass on Python 3.12. Pinned runtime requirements pass `pip check`.

The suite covers numbered and custom dice, preserved weighting, signed arithmetic, bonuses, keep-high/low, text-dice validation, malformed inputs, and result formatting. Exact forcing is compared with every reachable total on small numbered/custom combinations, including custom gaps, negative faces, subtracted pools, and highest/lowest rolls. Large numbered dice are allocated without enumerating their faces; bounded custom searches fail without changing the ordinary result.

Creator tests cover shorthand, one-setting replacement, owner/DM checks, one-use consumption, lasting luck, cross-server user targeting, custom text-face forcing, impossible results, malformed requests, duplicate deliveries, persistence, transaction rollback, old-table isolation, corrupt-setting fallback, changed creator IDs, and bounded receipt storage.

Transport tests serialize the actual one-command Discord tree, preserve the Gateway event dispatcher, check minimal intents, clear stale server commands, keep control state out of public replies, deliver private errors, handle blocked creator DMs, and respect Discord's message-size limit. Deployment tests validate the exact minimal bundle and Railway volume paths.

Source and `bot.pyz --check` succeed without credentials or a Discord login. The Dockerfile uses the same bundle check. Live Railway startup and command registration are checked separately during deployment. Automated Discord transport tests use mocked interactions; they do not send test messages to players.
