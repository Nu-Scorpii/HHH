# Version 3.1.0

- Added `/avatar`: IQ 1d20, six stat d20s, nation, conditional origin, bending check, and a Nomad element or non-bender combat style.
- Implemented the supplied ranges with deterministic boundaries: Fire families 1–49 / 50–79 / 80–94 / 95–100; Pressure point 81–100. Bending starts at 60.
- Added simple creator part controls, such as `!Rigger nation 30` and `!Rigger bending 100`, with the usual force, shift, luck, and cross-server user targeting.
- Shared the stable roll-control code with `/roll`; Avatar-only settings never affect ordinary custom rolls.
- Used modified outcomes for later decisions; skipped branches draw no dice. No Air bending is generated.
- Kept one active setting. A skipped one-use part clears privately after the targeted character; lasting luck remains active.
- Stored a whole character result, setting changes, and replay receipt in one transaction. Duplicate interactions return the same complete character.
- Preserved existing version-3 settings and the Railway volume. Added 92 regression tests; all 231 automated tests pass.

# Version 3.0.0

- Replaced the full game bot with one public command: `/roll`.
- Removed all character, combat, attendance, progression, FAQ, saved-die management, panels, and game-rule features from the runtime.
- Retained arbitrary numbered dice, mixed signed expressions, per-roll weighted or text faces, separate bonuses, and keep-high/low.
- Rebuilt Rigger around one active creator-only DM setting. Force/shift are one-use; good/bad is lasting. Each new setting replaces the previous one.
- Added simple shorthand, an optional user target across every server, and exact text-face forcing.
- Enforced legal faces and exact final totals. Impossible requests and bounded-search failures leave the roll normal, clear the one-use setting, and notify only the creator.
- Validated all input before drawing dice or consuming a setting. Made text-containing dice consistently nonnumeric.
- Committed settings and recent roll receipts atomically; repeated interactions do not consume controls twice. Kept old volume tables untouched and inactive.
- Removed stale global and server-specific game commands during startup. Removed the need for a server ID.
- Reduced runtime dependencies to discord.py and python-dotenv. Kept the four-file Railway Docker deployment and persistent-volume checks.
- Verified 139 focused automated tests, real Discord command serialization, packaged startup, and dependency compatibility.
