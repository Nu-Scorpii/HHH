from .battle import Battle
from .campaign import Campaign
from .core import Core
from .spar import Spar


class Game(Battle, Campaign, Spar, Core):
    """One transactional engine per bot process; campaigns are isolated by server."""
