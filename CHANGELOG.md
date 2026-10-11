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
