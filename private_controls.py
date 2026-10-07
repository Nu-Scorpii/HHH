"""Creator-only DM control. Never registered in the slash tree or public help."""

import json
import shlex
from datetime import datetime, timezone
from .dice import Die, parse, roll_expression, stat_roll
from .rules import GameError, require


class PrivateRolls:
    def __init__(self, store, owner_id, clock):
        self.store, self.owner_id, self.clock = store, int(owner_id), clock
        store.db.execute("CREATE TABLE IF NOT EXISTS private_settings (creator TEXT PRIMARY KEY, guild TEXT NOT NULL)")

    def handle(self, author_id, content, *, is_dm, guild_ids):
        # Check identity and DM context BEFORE parsing or responding.
        if not is_dm or int(author_id) != self.owner_id:
            return None
        if not content.startswith("!Rigger"):
            return None
        try:
            args = shlex.split(content)
            if not args or args[0] != "!Rigger":
                return None
            args = args[1:]
            if not args or args[0] == "help":
                return ("Creator controls (DM only)\n"
                        "`!Rigger server SERVER_ID` — select your server once\n"
                        "`!Rigger next PLAYER_ID 8` — next roll keeps 8\n"
                        "`!Rigger next any big 3` — next 3 matching rolls get a big result\n"
                        "`!Rigger next PLAYER_ID miss 2 speed 60` — 2 Speed rolls within 60 minutes\n"
                        "`!Rigger status` / `!Rigger clear` / `!Rigger clear RULE_ID` / `!Rigger audit`\n"
                        "Outcomes: a legal face, min, max, miss, success, big. Quote text faces.\n"
                        "Scopes: any, dice, check, attack, capture, task, defense, spar, or a stat.\n"
                        "Defaults: 1 use, any scope, 60 minutes. Specific player rules take priority.\n"
                        "Incompatible dice do not consume a rule. Raw dice pools force each face; modifiers stay unchanged.")
            action = args.pop(0)
            guilds = {str(x) for x in guild_ids}
            if action == "server":
                require(len(args) == 1 and args[0] in guilds, "Use a server ID where this bot is installed.")
                with self.store.transaction() as db:
                    db.execute("INSERT INTO private_settings VALUES(?,?) ON CONFLICT(creator) DO UPDATE SET guild=excluded.guild",
                               (str(self.owner_id), args[0]))
                return f"Selected server {args[0]}."
            selected = self.store.db.execute("SELECT guild FROM private_settings WHERE creator=?", (str(self.owner_id),)).fetchone()
            guild = selected[0] if selected else next(iter(guilds)) if len(guilds) == 1 else None
            require(guild in guilds, "First use !Rigger server SERVER_ID to select an installed server.")
            now = self.clock().timestamp()
            with self.store.transaction() as db:
                db.execute("DELETE FROM rig_rules WHERE remaining<=0 OR expires<=?", (now,))
                if action == "next":
                    require(2 <= len(args) <= 5, "Use !Rigger next PLAYER_ID|any OUTCOME [COUNT] [SCOPE] [MINUTES].")
                    target = args[0].strip("<@!>")
                    if target == "me":
                        target = str(self.owner_id)
                    require(target == "any" or target.isdecimal() and int(target) > 0, "Use a player ID, mention, me, or any.")
                    outcome = args[1]
                    count = int(args[2]) if len(args) > 2 else 1
                    scope = args[3].lower() if len(args) > 3 else "any"
                    minutes = int(args[4]) if len(args) > 4 else 60
                    require(1 <= count <= 100 and 1 <= minutes <= 1440, "Use 1–100 rolls and 1–1440 minutes.")
                    require(scope in {"any", "dice", "check", "attack", "capture", "task", "defense", "spar", "power", "speed", "wits", "heart"}, "Unknown scope.")
                    require(1 <= len(outcome) <= 40, "Use a short face or outcome.")
                    row = db.execute("INSERT INTO rig_rules(guild,target,outcome,scope,remaining,expires,creator) VALUES(?,?,?,?,?,?,?)",
                                     (guild, target, outcome, scope, count, now + minutes * 60, str(self.owner_id)))
                    return f"Queued rule #{row.lastrowid}: {target}, {scope}, {outcome}, {count} use(s), {minutes} minutes."
                if action == "clear":
                    require(len(args) <= 1, "Use !Rigger clear [RULE_ID].")
                    if args:
                        db.execute("DELETE FROM rig_rules WHERE guild=? AND id=?", (guild, int(args[0])))
                    else:
                        db.execute("DELETE FROM rig_rules WHERE guild=?", (guild,))
                    return "Cleared matching rules."
                if action == "status":
                    rows = db.execute("SELECT * FROM rig_rules WHERE guild=? ORDER BY id LIMIT 30", (guild,)).fetchall()
                    return "No queued rules." if not rows else "\n".join(
                        f"#{r['id']} · {r['target']} · {r['scope']} · {r['outcome']} · {r['remaining']} left · expires "
                        + datetime.fromtimestamp(r['expires'], timezone.utc).isoformat(timespec="minutes") for r in rows)
                if action == "audit":
                    rows = db.execute("SELECT * FROM rig_audit WHERE guild=? ORDER BY id DESC LIMIT 10", (guild,)).fetchall()
                    return "No applied overrides." if not rows else "\n".join(
                        f"Rule #{r['rule_id']} · player {r['target']} · {r['created']}\n"
                        f"Natural {r['natural'][:100]} → final {r['final'][:100]}" for r in rows)
                raise GameError("Unknown creator command. Use !Rigger help.")
        except (GameError, ValueError) as exc:
            return f"Could not apply that command: {exc}"

    def _rule(self, guild, user, scope, stat, compatible):
        rows = self.store.db.execute(
            "SELECT * FROM rig_rules WHERE guild=? AND target IN (?, 'any') AND scope IN (?, ?, 'any') "
            "AND remaining>0 AND expires>? ORDER BY CASE WHEN target=? THEN 0 ELSE 1 END,id",
            (str(guild), str(user), scope, stat or scope, self.clock().timestamp(), str(user))).fetchall()
        return next((r for r in rows if compatible(r['outcome'])), None)

    def _record(self, rule, user, natural, final):
        self.store.db.execute("UPDATE rig_rules SET remaining=remaining-1 WHERE id=? AND remaining>0", (rule['id'],))
        self.store.db.execute("INSERT INTO rig_audit(guild,target,rule_id,natural,final,created) VALUES(?,?,?,?,?,?)",
                              (rule['guild'], str(user), rule['id'], json.dumps(natural), json.dumps(final), self.clock().isoformat()))

    def stat(self, guild, user, scope, stat, sides, edge, pressure, rng):
        natural = stat_roll(sides, edge, pressure, rng)
        die = Die(sides=sides)
        rule = self._rule(guild, user, scope, stat, lambda outcome: die.forced(outcome) is not None)
        if not rule:
            return natural
        # Keep the natural companion die, without drawing any extra random dice.
        wanted = die.forced(rule['outcome'])
        final = dict(natural, rolls=list(natural['rolls']), kept=wanted)
        final['rolls'][0] = wanted
        if len(final['rolls']) == 2:
            final['rolls'][1] = max(final['rolls'][1], wanted) if final['mode'] == 'pressure' else min(final['rolls'][1], wanted)
        self._record(rule, user, natural, final)
        return final

    def expression(self, guild, user, expression, custom, keep, rng):
        terms = parse(expression, custom)
        dice = [die for _, term in terms if isinstance(term, list) for die in term]
        natural = roll_expression(expression, custom, rng, keep)
        rule = self._rule(guild, user, "dice", None, lambda outcome: all(d.forced(outcome) is not None for d in dice))
        if not rule:
            return natural
        final = roll_expression(expression, custom, rng, keep, force=rule['outcome'])
        self._record(rule, user, natural, final)
        return final
