"""Read the handbook from both normal source and the bundled zip application."""

from importlib.resources import files
from pathlib import Path
from .rules import GameError


def handbook_bytes():
    packaged = files('ua_bot').joinpath('PLAYER_HANDBOOK.md')
    if packaged.is_file():
        return packaged.read_bytes()
    source = Path(__file__).resolve().parent.parent/'docs'/'PLAYER_HANDBOOK.md'
    if source.is_file():
        return source.read_bytes()
    raise GameError('The player handbook is missing from this deployment. Re-upload the current bot.pyz package.')
