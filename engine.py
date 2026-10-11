"""Custom rolls and Avatar creation share one atomic creator control."""

import json
from .avatar import create_character
from .controls import COMMAND, HELP, describe, empty_setting, parse_command
from .dice import RNG, prepare
from .solver import Unavailable, force_face, force_total
from .errors import RollError, require


class DiceEngine:
    def __init__(self, store, owner_id, rng=RNG):
        require(type(owner_id) is int and owner_id > 0, 'BOT_OWNER_ID must be your Discord user ID.')
        self.store, self.owner_id, self.rng = store, owner_id, rng

    def private_message(self, author_id, content, *, is_dm, request_id=None):
        if not is_dm or author_id != self.owner_id or not isinstance(content, str) or not COMMAND.match(content):
            return None
        try:
            action, new = parse_command(content)
        except RollError as exc:
            return str(exc)
        signature = json.dumps([self.owner_id, content])
        with self.store.transaction():
            cached = self.store.receipt('dm', request_id, signature)
            if cached is not None:
                return cached
            setting = self.store.setting(self.owner_id)
            if action == 'help':
                reply = HELP
            elif action == 'status':
                reply = describe(setting) + ('\n\nLast affected roll:\n' + setting['last'] if setting['last'] else '')
            else:
                new = empty_setting() if action == 'off' else new
                new['last'] = setting['last']
                self.store.save_setting(self.owner_id, new)
                reply = describe(new)
            self.store.remember('dm', request_id, signature, reply)
            return reply

    def roll(self, user_id, guild_id, expression=None, *, faces=None, bonus=0, keep='all', request_id=None):
        # Invalid input must never draw dice or consume a one-use setting.
        plan = prepare(expression, faces=faces, bonus=bonus, keep=keep)
        return self.roll_plan(user_id, guild_id, plan, request_id=request_id)

    def _draw(self, user_id, guild_id, plan, setting, *, part=None):
        """Apply an eligible setting to one pool; the caller owns the transaction."""
        natural = plan.roll(self.rng)
        result, notice = natural, None
        mode = setting['mode']
        applies = (mode != 'off' and (setting['target'] is None or setting['target'] == str(user_id))
                   and (setting['part'] is None or setting['part'] == part))
        if not applies:
            return result, setting, notice
        try:
            if mode in ('good', 'bad'):
                if plan.numeric:
                    alternative = plan.roll(self.rng)
                    result = (max if mode == 'good' else min)((natural, alternative), key=lambda r: r['total'])
            elif mode == 'face':
                result = force_face(plan, natural, setting['value'])
            else:
                if natural['total'] is None:
                    raise Unavailable('text dice have no numeric total; use !Rigger face for a text label')
                target = setting['value'] if mode == 'force' else natural['total'] + setting['value']
                result = force_total(plan, natural, target)
        except Unavailable as exc:
            where = f'Avatar {part}: ' if part else ''
            notice = f'{where}Rigger could not apply: {exc}. The roll stayed normal; the one-use setting is cleared.'
        where = f'/avatar {part} · ' if part else ''
        summary = f"User {user_id} · server {guild_id} · {where}{plan.expression}\n{mode}: {natural['total']} → {result['total']}"
        if mode == 'face':
            summary = f"User {user_id} · server {guild_id} · {where}{plan.expression}\nText-face setting: {setting['value']}"
        elif mode in ('good', 'bad') and not plan.numeric:
            summary += '\nLuck skipped: text dice have no better/worse numeric total.'
        if notice:
            summary += '\n' + notice
        setting = empty_setting() if mode in ('force', 'shift', 'face') else dict(setting)
        setting['last'] = summary[:1000]
        return result, setting, notice

    def roll_plan(self, user_id, guild_id, plan, *, request_id=None):
        signature = json.dumps([self.owner_id, str(user_id), str(guild_id), plan.expression, plan.terms, plan.bonus, plan.keep],
                               default=lambda die: die.__dict__, sort_keys=True, ensure_ascii=False)
        with self.store.transaction():
            cached = self.store.receipt('roll', request_id, signature)
            if cached is not None:
                return {**cached, 'replayed': True}
            original = self.store.setting(self.owner_id)
            result, setting, notice = self._draw(user_id, guild_id, plan, original)
            if setting != original:
                self.store.save_setting(self.owner_id, setting)
            outcome = {'dice': result, 'notice': notice, 'replayed': False}
            self.store.remember('roll', request_id, signature, outcome)
            return outcome

    def avatar(self, user_id, guild_id, *, request_id=None):
        signature = json.dumps([self.owner_id, str(user_id), str(guild_id), 'avatar-v1'])
        with self.store.transaction():
            cached = self.store.receipt('avatar', request_id, signature)
            if cached is not None:
                return {**cached, 'replayed': True}
            original = setting = self.store.setting(self.owner_id)
            notices = []

            def draw(part, plan):
                nonlocal setting
                result, setting, notice = self._draw(user_id, guild_id, plan, setting, part=part)
                if notice:
                    notices.append(notice)
                return result

            character = create_character(draw)
            # A one-use conditional part belongs to this character, even if
            # that branch does not exist. Do not surprise the next player.
            part = original['part']
            targeted = original['target'] is None or original['target'] == str(user_id)
            if targeted and part and part not in character['rolls'] and original['mode'] in ('force', 'shift'):
                notice = f'Avatar {part} was not rolled for user {user_id}: this character did not need it. The one-use setting is cleared.'
                notices.append(notice)
                setting = empty_setting()
                setting['last'] = notice[:1000]
            if setting != original:
                self.store.save_setting(self.owner_id, setting)
            outcome = {'character': character, 'notice': '\n'.join(notices) or None, 'replayed': False}
            self.store.remember('avatar', request_id, signature, outcome)
            return outcome
